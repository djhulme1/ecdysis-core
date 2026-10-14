#!/usr/bin/env python3
"""Saha and Sinha's parametric series for pi and zeta(2), from string amplitudes: how fast they converge, computed exactly.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:f902dc5ca8b34322) is from Saha and Sinha,
"Field theory expansions of string theory amplitudes", Phys. Rev. Lett. 132, 221601 (2024), arXiv:2401.05733: "Our
considerations also lead to new QFT-inspired, parametric representations of the Zeta function and pi, which show fast
convergence."

Its registered test: refuted if, computed exactly from the paper's representation
pi = 4 + sum_{n>=1} (1/n!) (1/(n+lambda) - 4/(2n+1)) ((2n+1)^2/(4(n+lambda)) - n)_{n-1}, the sum of its first 60 terms
differs from pi by 5e-11 or more for any lambda in 10, 20, ..., 100; or its zeta(2) representation
-sum_{n>=1} (2 lambda + n)/(lambda n^2 n!) (-n lambda/(n+lambda))_n with lambda = 41.5 differs from pi^2/6 by 5e-16 or
more after 80 terms. The bounds are twice the paper's counts ("with lambda between 10-100 takes 30 terms"; "15 decimal
places retaining only 40 terms").

The input is the paper's v5 e-print from arXiv, checked against its SHA-256 and read as data (the tar opened with the
standard library and its TeX read as text; nothing in it is run). Every rule below was fixed before any partial sum was
computed; the seed is not used, as nothing here is random.

1. The source. With its TeX comments removed and its whitespace collapsed, arXiv_final.tex must hold the two formulas
   exactly as written in FORMULAS below, and the sentences that state their speed (SENTENCES); otherwise the run is
   refused. The series computed are those formulas: (a)_m is the rising factorial a (a+1) ... (a+m-1), (a)_0 = 1.
2. Exactness. Each term is an exact rational (lambda is rational); the terms are summed in decimal arithmetic carried to
   PRECISION digits, so a partial sum is exact to far better than any threshold here: the run stops unless the rounding
   bound, 4 (SEARCH + 1) max|S_n| 10^(1 - PRECISION), is below 1e-30. pi is computed by Machin's formula in integers to
   the same precision.
3. The test's eleven conditions: for each lambda in 10, 20, ..., 100, |S_60(lambda) - pi| < 5e-11, where S_N is 4 plus
   the first N terms; and |Z_80(41.5) - pi^2/6| < 5e-16, where Z_N is the first N terms of the zeta(2) series.
   test_passed is 1 if all eleven hold.
4. Beside the test, against the paper's counts: for each lambda, the least N from which every S_n, n = N to N + 40,
   is within 5e-11 of pi (the paper: 30 for lambda from 10 to 100), and the same within 1e-10; the least such N for
   zeta(2) at 41.5 within 5e-16 (the paper: 40); and the two classical series the paper compares, from the
   Euler-Boole expansion of the alternating tail (pi - 4 sum_{k<N} (-1)^k/(2k+1) = (-1)^N (1/N - 1/(4N^3) + 5/(16N^5)
   - ...), to its fifth term) and from sum_{n>N} 1/n^2 = 1/N - 1/(2N^2) + 1/(6N^3) - ... (Euler-Maclaurin, to its fifth
   term): Madhava's error after the paper's "5 billion
   terms" and the terms it needs for 5e-11, and the error of sum 1/n^2 after "50 million terms" and the terms it needs
   for 5e-16.
5. Controls, known answers: Machin's pi against its first 50 printed decimals; the rising factorial (1/2)_3 = 15/8;
   each pi summand at lambda = 10^15 within 1e-12 of Madhava's (-1)^n 4/(2n+1) for n = 1 to 6, as the paper says of the
   limit; each zeta(2) summand at lambda = 10^-15 within 1e-12 of 1/n^2 for n = 1 to 6, as the paper says of lambda = 0;
   and, within 1e-30, the Euler-Boole expansion against an exact partial sum of Madhava's series at N = 2000 and the
   Euler-Maclaurin expansion against an exact partial sum of sum 1/n^2 at N = 2000.

What it cannot check: the derivation of the representations from the string amplitude; only the printed series and
what they converge to.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 pi/saha.py
"""

import decimal
import hashlib
import io
import json
import os
import re
import sys
import tarfile
from fractions import Fraction

INPUTS = {"eprint": ("arXiv-2401.05733v5.tar.gz", "3e9d9f0c35c546b04cbb747acf74ff8d7440d6f4c26ac6e05f25b6872cb82cdd")}
TEX = "arXiv_final.tex"
FORMULAS = (
    r"\pi=4+\sum_{n=1}^\infty \frac{1}{n!}\left(\frac{1}{n+\lambda}-\frac{4}{2n+1}\right)\left(\frac{(2n+1)^2}"
    r"{4(n+\lambda)}-n\right)_{n-1}.",
    r"-\sum_{n=1}^{\infty}\frac{(2 \lambda +n) }{\lambda n^2 n! } \left(-\frac{n \lambda }{n+\lambda}\right)_n"
    r"=\zeta\left(2\right).",
)
SENTENCES = (
    "While this series takes 5 billion terms to converge to 10 decimal places, the new representation with $\\lambda$ "
    "between $10-100$ takes 30 terms.",
    "Putting $\\lambda=41.5$, we get convergence to 15 decimal places retaining only 40 terms, while $\\sum 1/n^2$ would "
    "need 50 million terms!",
)
LAMBDAS = tuple(range(10, 101, 10))
ZETA_LAMBDA = Fraction(83, 2)
N_PI, N_ZETA = 60, 80
TOL_PI, TOL_PI_LOOSE, TOL_ZETA = Fraction(5, 10 ** 11), Fraction(1, 10 ** 10), Fraction(5, 10 ** 16)
PRINTED = {"pi_terms": 30, "zeta_terms": 40, "madhava_terms": 5 * 10 ** 9, "basel_terms": 5 * 10 ** 7}
PRECISION = 160
SEARCH = 300
PI50 = "3.14159265358979323846264338327950288419716939937510"
OUTPUTS = ("source", "pi_errors", "worst_pi_error", "zeta_error", "least_terms_pi", "least_terms_pi_loose",
           "least_terms_zeta", "madhava", "basel", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


def tex_of(eprint):
    with tarfile.open(fileobj=io.BytesIO(eprint), mode="r:gz") as t:
        try:
            member = t.getmember(TEX)
        except KeyError:
            raise Refused(f"the e-print holds no {TEX}") from None
        return t.extractfile(member).read().decode("utf-8")


def flatten(tex):
    """TeX comments removed (an unescaped % to the end of its line), then whitespace collapsed."""
    lines = [re.sub(r"(?<!\\)%.*$", "", line) for line in tex.split("\n")]
    return re.sub(r"\s+", " ", " ".join(lines))


def check_source(tex):
    flat = flatten(tex)
    for s in FORMULAS + SENTENCES:
        if s not in flat:
            raise Refused(f"the e-print does not hold, as read: {s[:80]!r}")


def poch(a, m):
    """The rising factorial (a)_m, exactly."""
    out = Fraction(1)
    for k in range(m):
        out *= a + k
    return out


def pi_term(n, lam):
    fact = Fraction(1)
    for k in range(2, n + 1):
        fact *= k
    a = Fraction((2 * n + 1) ** 2) / (4 * (n + lam)) - n
    return (1 / fact) * (Fraction(1) / (n + lam) - Fraction(4, 2 * n + 1)) * poch(a, n - 1)


def zeta_term(n, lam):
    fact = Fraction(1)
    for k in range(2, n + 1):
        fact *= k
    return -(2 * lam + n) / (lam * n * n * fact) * poch(-Fraction(n) * lam / (n + lam), n)


def dec(x):
    return decimal.Decimal(x.numerator) / decimal.Decimal(x.denominator)


def partial_sums(term, lam, start, count):
    """[S_0, S_1, ..., S_count] in decimal arithmetic, each term exact before its division."""
    s, out = decimal.Decimal(start), [decimal.Decimal(start)]
    for n in range(1, count + 1):
        s += dec(term(n, lam))
        out.append(s)
    return out


def machin_pi(digits):
    """pi as a Decimal to the given digits: 16 arctan(1/5) - 4 arctan(1/239) in integers."""
    scale = 10 ** (digits + 10)

    def arctan_inv(x):
        total, term, k, sign, x2 = 0, scale // x, 1, 1, x * x
        while term:
            total += sign * (term // k)
            term //= x2
            k += 2
            sign = -sign
        return total
    v = 16 * arctan_inv(5) - 4 * arctan_inv(239)
    return decimal.Decimal(v) / decimal.Decimal(scale)


def least_stable(sums, target, tol, window=40):
    """The least N from which every partial sum up to N + window is within tol of the target, or None."""
    tol = dec(tol)
    for n in range(len(sums) - window):
        if all(abs(sums[m] - target) < tol for m in range(n, n + window + 1)):
            return n
    return None


def madhava_error(n):
    """|pi - 4 sum_{k<n} (-1)^k/(2k+1)| by the Euler-Boole expansion, to its fifth term (the Euler numbers)."""
    n = decimal.Decimal(n)
    return 1 / n - 1 / (4 * n ** 3) + 5 / (16 * n ** 5) - 61 / (64 * n ** 7) + 1385 / (256 * n ** 9)


def basel_error(n):
    """sum_{k>n} 1/k^2 by its Euler-Maclaurin expansion, to its fifth term (the Bernoulli numbers)."""
    n = decimal.Decimal(n)
    return 1 / n - 1 / (2 * n ** 2) + 1 / (6 * n ** 3) - 1 / (30 * n ** 5) + 1 / (42 * n ** 7)


def terms_needed(error, tol):
    """The least n with error(n) < tol, for an error falling like 1/n."""
    lo, hi = 1, 1
    while error(hi) >= tol:
        hi *= 2
    while lo < hi:
        mid = (lo + hi) // 2
        if error(mid) < tol:
            hi = mid
        else:
            lo = mid + 1
    return lo


def conditions(err, zerr):
    """The test's eleven conditions, from |S_60 - pi| by lambda and |Z_80 - zeta(2)| at 41.5."""
    cond = {f"lambda = {lam}: |S_60 - pi| < 5e-11": err[lam] < dec(TOL_PI) for lam in LAMBDAS}
    cond["lambda = 41.5: |Z_80 - zeta(2)| < 5e-16"] = zerr < dec(TOL_ZETA)
    return cond


def controls_known(pi):
    pi_ok = str(+pi)[:52] == PI50
    poch_ok = poch(Fraction(1, 2), 3) == Fraction(15, 8)
    big = Fraction(10 ** 15)
    limit_ok = all(abs(pi_term(n, big) - Fraction(4 * (-1) ** n, 2 * n + 1)) < Fraction(1, 10 ** 12) for n in range(1, 7))
    small = Fraction(1, 10 ** 15)
    zero_ok = all(abs(zeta_term(n, small) - Fraction(1, n * n)) < Fraction(1, 10 ** 12) for n in range(1, 7))
    tiny = decimal.Decimal(10) ** -30
    m = sum(Fraction(4 * (-1) ** k, 2 * k + 1) for k in range(2000))
    boole_ok = abs(abs(pi - dec(m)) - madhava_error(2000)) < tiny
    b = sum(Fraction(1, k * k) for k in range(1, 2001))
    maclaurin_ok = abs((pi * pi / 6 - dec(b)) - basel_error(2000)) < tiny
    return {"Machin's pi gives its first 50 printed decimals": pi_ok,
            "the rising factorial gives (1/2)_3 = 15/8": poch_ok,
            "at lambda = 1e15 the pi summands are Madhava's to 1e-12": limit_ok,
            "at lambda = 1e-15 the zeta(2) summands are 1/n^2 to 1e-12": zero_ok,
            "the Euler-Boole expansion matches an exact Madhava sum at N = 2000": bool(boole_ok),
            "the Euler-Maclaurin expansion matches an exact sum of 1/n^2 at N = 2000": bool(maclaurin_ok)}


def sci(x):
    return f"{float(x):.2e}"


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    decimal.getcontext().prec = PRECISION
    raw = read_bytes(os.path.join(inputs, INPUTS["eprint"][0]), INPUTS["eprint"][1])
    check_source(tex_of(raw))
    pi = machin_pi(PRECISION)
    zeta2 = pi * pi / 6

    sums = {lam: partial_sums(pi_term, Fraction(lam), 4, SEARCH) for lam in LAMBDAS}
    zsums = partial_sums(zeta_term, ZETA_LAMBDA, 0, SEARCH)
    largest = max(abs(x) for x in [x for lam in LAMBDAS for x in sums[lam]] + zsums)
    bound = largest * 4 * (SEARCH + 1) * decimal.Decimal(10) ** (1 - PRECISION)
    if not bound < decimal.Decimal(10) ** -30:
        raise AssertionError(f"the decimal sums are not certain to 1e-30: rounding bound {bound}")
    err = {lam: abs(sums[lam][N_PI] - pi) for lam in LAMBDAS}
    zerr = abs(zsums[N_ZETA] - zeta2)
    cond = conditions(err, zerr)

    least = {lam: least_stable(sums[lam], pi, TOL_PI) for lam in LAMBDAS}
    least_loose = {lam: least_stable(sums[lam], pi, TOL_PI_LOOSE) for lam in LAMBDAS}
    least_zeta = least_stable(zsums, zeta2, TOL_ZETA)
    m_err = madhava_error(PRINTED["madhava_terms"])
    m_need = terms_needed(madhava_error, dec(TOL_PI))
    b_err = basel_error(PRINTED["basel_terms"])
    b_need = terms_needed(basel_error, dec(TOL_ZETA))
    controls = controls_known(pi)

    def listing(d):
        return ", ".join(f"{lam} {d[lam]}" for lam in LAMBDAS)
    values = {
        "source": "the e-print holds both series and both speeds as read",
        "pi_errors": "|S_60 - pi|: " + ", ".join(f"{lam} {sci(err[lam])}" for lam in LAMBDAS),
        "worst_pi_error": float(f"{float(max(err.values())):.3e}"),
        "zeta_error": float(f"{float(zerr):.3e}"),
        "least_terms_pi": "terms for 5e-11, by lambda: " + listing(least),
        "least_terms_pi_loose": "terms for 1e-10, by lambda: " + listing(least_loose),
        "least_terms_zeta": f"zeta(2) at 41.5: {least_zeta} terms for 5e-16 (printed 40)",
        "madhava": (f"Madhava: error {sci(m_err)} after 5e9 terms; {m_need:.3e} terms for 5e-11"),
        "basel": f"sum 1/n^2: error {sci(b_err)} after 5e7 terms; {b_need:.3e} terms for 5e-16",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": {k: {"name": n, "sha256": s} for k, (n, s) in INPUTS.items()},
              "conditions": cond, "controls": controls, "largest_partial_sum": sci(largest),
              "rounding_bound": sci(bound),
              "errors_at_60": {str(lam): str(err[lam]) for lam in LAMBDAS}, "zeta_error_at_80": str(zerr),
              "least": {str(k): v for k, v in least.items()}, "least_loose": {str(k): v for k, v in least_loose.items()},
              "least_zeta": least_zeta,
              "errors_at_30": {str(lam): str(abs(sums[lam][30] - pi)) for lam in LAMBDAS},
              "zeta_error_at_40": str(abs(zsums[40] - zeta2)),
              "madhava_error_5e9": str(m_err), "madhava_terms_5e-11": m_need,
              "basel_error_5e7": str(b_err), "basel_terms_5e-16": b_need}
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
        sys.exit(f"saha: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
