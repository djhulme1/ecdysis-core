#!/usr/bin/env python3
"""Brent's equivalence: one iteration of the Borweins' quartic algorithm for pi gives exactly what two iterations of
the Gauss-Legendre algorithm give.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:ba4382a3c853e871) is from Brent, "The
Borwein brothers, Pi and the AGM" (arXiv:1802.07558; Springer Proceedings in Mathematics and Statistics 313, 2020):
"We show that an iteration of the Borwein-Borwein quartic algorithm for pi is equivalent to two iterations of the
Gauss-Legendre quadratic algorithm for pi, in the sense that they produce exactly the same sequence of approximations
to pi if performed using exact arithmetic."

Its registered test: refuted if, in 180,200-digit arithmetic, the paper's Algorithm BB4 (y_0 = sqrt2 - 1,
z_0 = 2y_0^2; y_{n+1} = (1 - (1 - y_n^4)^{1/4})/(1 + (1 - y_n^4)^{1/4}), z_{n+1} = z_n(1 + y_{n+1})^4
- 2^{2n+3}y_{n+1}(1 + y_{n+1} + y_{n+1}^2), pi_n = 1/z_n) and Algorithm GL (a_0 = 1, b_0 = 1/sqrt2, s_0 = 1/4;
a_{n+1} = (a_n + b_n)/2, b_{n+1} = sqrt(a_n b_n), s_{n+1} = s_n - 2^n(a_n - a_{n+1})^2) give
|pi_n - a_{2n+1}^2/s_{2n}| above 10^-180000 for any n from 0 to 8, or pi - pi_n other than Table 6's 50-digit values
for n = 0 to 4.

Standard library only: Python's decimal module (libmpdec), every operation correctly rounded, so the run repeats
digit for digit anywhere. The one input is the paper's source as arXiv serves it (v3, a gzipped tar of its TeX),
checked against its SHA-256 and size; the statements of both algorithms, the corollary under test, the bound and every
printed number used below must be found in it verbatim, or the run is refused (rule 7). Every rule was fixed before
any seed existed; the seed is not used, as nothing here is random.

1. Arithmetic. P = 180,200 significant digits, rounding half to even: the test's "180,200-digit arithmetic".
2. The iterations, as section 4 of the paper prints them. Algorithm BB4 for n = 0 to 8, its fourth root taken as two
   square roots; Algorithm GL to a_17 and s_16, with c_{n+1} = a_n - a_{n+1} as printed (its lower approximation,
   Algorithm GL1's, is a_{n+1}^2/s_n).
3. The comparison. D_n = |pi_n - a_{2n+1}^2/s_{2n}| for n = 0 to 8, in the same arithmetic; its agreement digits are
   floor(-log10 D_n), or P when D_n is 0. The test's bound 10^-180000 is 10^-(P - 200).
4. The reference pi. The Chudnovskys' series, checked against Ramanujan's of 1914, both by binary splitting in exact
   integers and divided out at P + 120 digits, as pi/agm.py computes them (imported from it).
5. Table 6. For n = 0 to 4, pi - pi_n rounded half to even to 50 significant digits must be the printed value. The
   table labels its rows by GL1's n (0, 2, 4, 6, 8); they are BB4's pi_0 to pi_4, by the corollary under test. Before
   registering, all five matched so; three of them differ from the truncated digits, so the table rounds.
6. What the agreement means. The correct digits of pi_n, d_n = floor(-log10(pi - pi_n)), are reported for n = 0 to 8.
   At n = 8 (pi - pi_8 is about 3 x 10^-178,825) the two algorithms agree to over a thousand more digits than either
   agrees with pi, so the test does not compare two values that have both converged; pi - pi_9 would be about
   10^-715,000, beyond any precision that fits here, which is why the test stops at n = 8.
7. The source. Each string in VERBATIM, each row of Tables 5 and 6 as printed, and the polynomial P(x) of section 5
   (parsed term by term) must be in the TeX exactly as this file holds them.

test_passed is 1 if D_n <= 10^-180000 for every n from 0 to 8 and all five Table 6 values match; else 0.

Controls, each reported:
(a) the references: rule 4's agreement and first 50 decimals;
(b) precision: rules 2 and 3 again at P + 100 digits; the largest D_n must fall by a factor of at least 10^90, so what
    remains at P is rounding and not a difference between the algorithms;
(c) Table 5: BB4's error and its ratio to the bound (eq. BB4_bound), to ten significant digits, for n = 0 to 8 (18
    numbers); each of ours must lie within one unit of the printed last digit, and how many match exactly when
    rounded as printed is reported (before registering, 16: the n = 2 row reads as truncated, not rounded);
(d) the bound: 0 < pi - pi_n < pi^2 4^(n+2) exp(-2 pi 4^n) for n = 0 to 8;
(e) the paper's own argument for its second row: the degree-8 polynomial P(x) it prints vanishes at pi_1 and at
    a_3^2/s_2 (within 10^-2900, at 3,000 digits) and not at pi;
(f) the test can fail: with y_0 raised by 10^-30, D_n exceeds 10^-2800 at 3,000 digits for some n (the same rules
    give D_n below it for every n without the change);
(g) and so it does with GL1 one step out of line, pi_n against a_{2n+2}^2/s_{2n+1}.

What it cannot check: exact arithmetic itself (rule 1 is the test's finite stand-in, 200 digits above its rounding);
steps beyond n = 8; Brent's proof, which this run observes and does not prove.

Writes results/outputs.json (19 values) and results/detail.json. Run with: python3 pi/brent.py
"""

import decimal
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tarfile
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_agm", os.path.join(HERE, "agm.py"))
agm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agm)
context, correct_digits, compare, Refused = agm.context, agm.correct_digits, agm.compare, agm.Refused

PRECISION = 180_200                 # rule 1
GAP = 200                           # rule 3: the bound is 10^-(P - GAP), 10^-180000 at P
N_MAX = 8                           # BB4's pi_0 to pi_8
MORE = 100                          # control (b)
FALL = 90                           # control (b): the largest D_n must fall by at least 10^FALL
CONTROL_PREC = 3000                 # controls (e) to (g)
POLY_ZERO = 2900                    # control (e)
PERTURB = D("1e-30")                # control (f)
RATIO_PREC = 60                     # controls (c) and (d)
TABLE6_DIGITS = 50                  # rule 5

INPUT = ("arXiv-1802.07558v3.tar.gz", "323364b0ecec564f7758ac3c19bd9bdeb323d20a449daad4c75b299216330310", 36782)
TEX = "rpb269v3.tex"

# Rule 7: the statements this file implements, as the TeX prints them.
VERBATIM = (
    r"&y_0 := \sqrt{2}-1;\;\; z_0 := 2y_0^2;\\",
    r"&\hspace*{2em}\textbf{output } \pi_n := 1/z_n\,;\\",
    r"&\hspace{4em}y_{n+1} := \frac{1-(1-y_n^4)^{1/4}}",
    r"{1+(1-y_n^4)^{1/4}}\;;\\",
    r"z_n(1+y_{n+1})^4 - 2^{2n+3}y_{n+1}(1+y_{n+1}+y_{n+1}^2).",
    r"&a_0 := 1;\; b_0 := 1/\sqrt{2};\; s_0 := \textstyle\frac{1}{4}.\\",
    r"&\hspace*{2em}a_{n+1} := (a_n+b_n)/2;\\",
    r"&\hspace*{2em}c_{n+1} := a_n - a_{n+1};\\",
    r"&\hspace*{2em}\textbf{output } (a_{n+1}^2/s_n,\; a_{n}^2/s_n).\\",
    r"&\hspace*{4em}b_{n+1} := \sqrt{a_n b_n};\\",
    r"&\hspace*{4em}s_{n+1} := s_n - 2^n\,c_{n+1}^2.",
    r"Algorithm BB4 is equivalent to Algorithm GL1 doubled, in the",
    r"sense that \[\pi_n = a_{2n+1}^2/s_{2n},\] where $\pi_n$ is as in Algorithm",
    r"0 < \pi - \pi_n < \pi^2\,4^{n+2}\exp(-2\pi\, 4^n).",
)

# Table 6 (GL1's n = 2k, BB4's k): pi - pi_k to 50 significant digits, mantissa and exponent as printed.
TABLE6 = (
    (0, "2.2737909121669818966095465906980480562749752399816", "-1"),
    (2, "7.3762509563132989512968071098827321760295030264154", "-9"),
    (4, "5.4721091456899418327485331789641785565936917028248", "-41"),
    (6, "2.3085807149343902668213207343869568303303472423996", "-171"),
    (8, "1.1109549335576998257002904117322306941479378545140", "-694"),
)

# Table 5: n -> (pi - pi_n, its ratio to the bound (eq. BB4_bound)), as printed.
TABLE5 = (
    (0, "2.273790912e-1", "0.7710517124"),
    (1, "7.376250956e-9", "0.9602112619"),
    (2, "5.472109145e-41", "0.9900528160"),
    (3, "2.308580715e-171", "0.9975132040"),
    (4, "1.110954934e-694", "0.9993783010"),
    (5, "9.244416653e-2790", "0.9998445753"),
    (6, "6.913088685e-11172", "0.9999611438"),
    (7, "3.376546688e-44702", "0.9999902860"),
    (8, "3.002256862e-178825", "0.9999975715"),
)

# Section 5: the minimal polynomial of a_3^2/s_2 and pi_1, coefficients by degree.
POLY = (1, -1635840576, -343853312, 60576043008, 1865242664960, -16779556159488, 37529045696512, -29726424956928,
        6181548457984)


def load(inputs):
    """The paper's TeX from the e-print, after checking the e-print's hash and size."""
    with open(os.path.join(inputs, INPUT[0]), "rb") as fh:
        blob = fh.read()
    if len(blob) != INPUT[2] or hashlib.sha256(blob).hexdigest() != INPUT[1]:
        raise Refused(f"{INPUT[0]}: not the committed input")
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        return tar.extractfile(TEX).read().decode("utf-8")


def poly_of(tex):
    """The coefficients of P(x) as section 5 prints them, by degree."""
    m = re.search(r"P\(x\) :=&(.*?)\\end\{align\*\}", tex, re.S)
    if not m:
        raise Refused("P(x) is not in the source")
    body = re.sub(r"\\\\\[-?\d+pt\]|\\;|&", " ", m.group(1)).replace("\n", " ").strip().rstrip(".")
    coef = {}
    for sign, digits, x, deg in re.findall(r"([+-]?)\s*(\d+)\s*(x(?:\^(\d+))?)?", body):
        d = (int(deg) if deg else 1) if x else 0
        if d in coef:
            raise Refused(f"P(x): degree {d} printed twice")
        coef[d] = -int(digits) if sign == "-" else int(digits)
    return tuple(coef.get(d, 0) for d in range(max(coef) + 1))


def verbatim(tex):
    """Rule 7: how many of the strings this file relies on are in the TeX; refused unless all."""
    wanted = list(VERBATIM)
    wanted += [f"{n} &\\;\\; ${m}\\text{{e{e}}}$" for n, m, e in TABLE6]
    wanted += [f"{n} & \\, {err} & \\, {ratio} \\\\" for n, err, ratio in TABLE5]
    missing = [w for w in wanted if w not in tex]
    if missing:
        raise Refused(f"not in the source as printed: {missing}")
    if poly_of(tex) != POLY:
        raise Refused(f"P(x) in the source is {poly_of(tex)}, not {POLY}")
    return len(wanted) + 1


def bb4(prec, n_max, y0_shift=0):
    """Algorithm BB4 at prec digits: [pi_0, ..., pi_{n_max}]."""
    out = []
    with context(prec):
        y = D(2).sqrt() - 1 + y0_shift
        z = 2 * y * y
        for n in range(n_max + 1):
            out.append(1 / z)
            if n < n_max:
                r = (1 - y ** 4).sqrt().sqrt()
                y = (1 - r) / (1 + r)
                z = z * (1 + y) ** 4 - 2 ** (2 * n + 3) * y * (1 + y + y * y)
    return out


def gl1(prec, n_max):
    """Algorithm GL at prec digits: [a_{n+1}^2/s_n for n = 0..n_max], GL1's approximations."""
    out = []
    with context(prec):
        a, b, s = D(1), 1 / D(2).sqrt(), D(1) / 4
        for n in range(n_max + 1):
            a1 = (a + b) / 2
            c1 = a - a1
            out.append(a1 * a1 / s)
            if n < n_max:
                b = (a * b).sqrt()
                s = s - 2 ** n * c1 * c1
            a = a1
    return out


def agreement(diff, prec):
    """Rule 3: floor(-log10 |diff|), or prec when diff is 0."""
    return prec if diff == 0 else correct_digits(diff)


def compared(prec, n_max, y0_shift=0, step=0):
    """Rules 2 and 3: [(D_n, agreement digits)] and BB4's [pi_n], with GL1's index 2n + step."""
    quartic = bb4(prec, n_max, y0_shift)
    quadratic = gl1(prec, 2 * n_max + step)
    rows = []
    with context(prec):
        for n, p in enumerate(quartic):
            diff = abs(p - quadratic[2 * n + step])
            rows.append((diff, agreement(diff, prec)))
    return rows, quartic


def passes(rows, prec):
    """The test's first clause: D_n <= 10^-(prec - GAP) for every n."""
    bound = D((0, (1,), -(prec - GAP)))
    return all(diff <= bound for diff, _ in rows)


def table6(quartic, pi, prec):
    """Rule 5: pi - pi_k rounded half to even to 50 significant digits against each printed value."""
    rounder = decimal.Context(prec=TABLE6_DIGITS, rounding=decimal.ROUND_HALF_EVEN, Emax=decimal.MAX_EMAX,
                              Emin=decimal.MIN_EMIN)
    truncator = decimal.Context(prec=TABLE6_DIGITS, rounding=decimal.ROUND_DOWN, Emax=decimal.MAX_EMAX,
                                Emin=decimal.MIN_EMIN)
    rows = []
    with context(prec):
        for k, (label, mant, exp) in enumerate(TABLE6):
            err = pi - quartic[k]
            printed = D(f"{mant}e{exp}")
            rows.append({"bb4_n": k, "gl1_n": label, "printed": f"{mant}e{exp}", "ours": f"{err:.60e}",
                         "matched": rounder.plus(err) == printed, "truncation_matches": truncator.plus(err) == printed})
    return rows


def bound_of(n, pi):
    """pi^2 4^(n+2) exp(-2 pi 4^n), in the current context."""
    return pi * pi * 4 ** (n + 2) * (-2 * pi * 4 ** n).exp()


def table5(quartic, pi, prec):
    """Controls (c) and (d): Table 5's 18 numbers, and the bound for every n."""
    rows, bounds = [], []
    errors = []
    with context(prec):
        for p in quartic:
            errors.append(pi - p)
    with context(RATIO_PREC):
        pi_r = +pi
        for (n, perr, pratio), err in zip(TABLE5, errors):
            err = +err
            b = bound_of(n, pi_r)
            ratio = err / b
            rows.append(dict(compare(err, perr, f"{err:.9e}"), n=n, column="error"))
            rows.append(dict(compare(ratio, pratio, f"{ratio:.10f}"), n=n, column="ratio"))
            bounds.append({"n": n, "held": bool(0 < err < b), "ratio": f"{ratio:.15f}"})
    return rows, bounds


def polynomial(pi):
    """Control (e): P at pi_1 and at a_3^2/s_2 within 10^-POLY_ZERO of 0, and P(pi) above 1 in size."""
    quartic = bb4(CONTROL_PREC, 1)
    quadratic = gl1(CONTROL_PREC, 2)
    with context(CONTROL_PREC):
        pi_c = +pi

        def p(x):
            acc = D(0)
            for c in reversed(POLY):
                acc = acc * x + c
            return acc

        at = {"pi_1": p(quartic[1]), "a3^2/s2": p(quadratic[2]), "pi": p(pi_c)}
    small = D((0, (1,), -POLY_ZERO))
    ok = abs(at["pi_1"]) < small and abs(at["a3^2/s2"]) < small and abs(at["pi"]) > 1
    return ok, {k: f"{v:.6e}" for k, v in at.items()}


def run(inputs="inputs", results="results", precision=PRECISION, n_max=N_MAX, progress=None):
    say = progress or (lambda *_: None)
    tex = load(inputs)
    found = verbatim(tex)
    say("source", found, "strings found verbatim")
    pi, ref = agm.references(precision + agm.REF_EXTRA)
    if not (ref["agree"] and ref["first50"]):
        raise Refused(f"rule 4: the two references disagree or do not begin as pi does: {ref}")
    say("references", ref)
    rows, quartic = compared(precision, n_max)
    say("compared", [a for _, a in rows])
    more, _ = compared(precision + MORE, n_max)
    say("compared at P + MORE", [a for _, a in more])
    with context(precision + agm.REF_EXTRA):
        ds = [correct_digits(pi - p) for p in quartic]
        positive = [bool(pi - p > 0) for p in quartic]
    t6 = table6(quartic, pi, precision + agm.REF_EXTRA)
    t5, bounds = table5(quartic, pi, precision + agm.REF_EXTRA)
    poly_ok, poly_at = polynomial(pi)
    pert, _ = compared(CONTROL_PREC, n_max, y0_shift=PERTURB)
    plain, _ = compared(CONTROL_PREC, n_max)
    shifted, _ = compared(CONTROL_PREC, n_max, step=1)
    worst = max(range(len(rows)), key=lambda n: (rows[n][0], -n))
    agree = rows[worst][1]
    agree_more = min(a for _, a in more)
    checks = {
        "references": bool(ref["agree"] and ref["first50"]),
        "precision": agree_more >= agree + FALL,
        "table5": all(r["within"] for r in t5),
        "bounds": all(b["held"] for b in bounds) and all(positive),
        "polynomial": poly_ok,
        "perturbed_fails": passes(plain, CONTROL_PREC) and not passes(pert, CONTROL_PREC),
        "shifted_fails": not passes(shifted, CONTROL_PREC),
    }
    say("controls", checks)
    test = passes(rows, precision) and all(r["matched"] for r in t6)
    out = {
        "precision": precision,
        "agree_digits": agree,
        "worst_n": worst,
        "agree_digits_more": agree_more,
        "excess_at_last": rows[-1][1] - ds[-1],
        "correct_digits": ",".join(str(d) for d in ds),
        "table6_matched": sum(r["matched"] for r in t6),
        "table6_total": len(t6),
        "table5_matched": sum(r["matched"] for r in t5),
        "table5_total": len(t5),
        "bounds_held": int(checks["bounds"]),
        "poly_vanishes": int(poly_ok),
        "refs_agree": int(checks["references"]),
        "perturbed_fails": int(checks["perturbed_fails"]),
        "shifted_fails": int(checks["shifted_fails"]),
        "verbatim": found,
        "controls_passed": sum(checks.values()),
        "controls_total": len(checks),
        "test_passed": int(test),
    }
    detail = {
        "rules": {"precision": precision, "n_max": n_max, "gap": GAP, "more": MORE, "fall": FALL,
                  "control_precision": CONTROL_PREC, "input": list(INPUT)},
        "references": ref,
        "comparison": [{"n": n, "D_n": "0" if d == 0 else f"{d:.6e}", "agreement_digits": a,
                        "agreement_digits_more": more[n][1], "correct_digits": ds[n], "below_pi": positive[n]}
                       for n, (d, a) in enumerate(rows)],
        "table6": t6,
        "table5": t5,
        "bounds": bounds,
        "polynomial": poly_at,
        "perturbed": [a for _, a in pert],
        "plain_at_control_precision": [a for _, a in plain],
        "shifted": [a for _, a in shifted],
        "controls": checks,
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
        out, _ = run(progress=lambda *a: print("brent:", *a, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"brent: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
