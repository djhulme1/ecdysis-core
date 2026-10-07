#!/usr/bin/env python3
"""The hexadecimal digits of zeta(3) and zeta(5) from the ten millionth place, recomputed: Broadhurst's own formulas,
read from his paper's source, and an independent series for zeta(3).

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:b5a5d5e466728267) is from D. J. Broadhurst,
"Polylogarithmic ladders, hypergeometric series and the ten millionth digits of zeta(3) and zeta(5)" (arXiv:math/9803067,
1998): "We compute digits of zeta(3) and zeta(5), starting at the ten millionth hexadecimal place." Its registered test:
refuted if the 64 hexadecimal digits of zeta(3) beginning at the 10,000,000th hexadecimal place after the point (that
digit first) are not the string section 4 of the paper reports, or those of zeta(5) are not its other string, by any
correct computation of the two constants.

The input is the paper's source as arXiv serves it (a gzipped TeX file), checked against its SHA-256 and size and read
as data. Every rule below was fixed before any seed existed.

1. The paper, read. From the source come: the definition (S) of S_{n,p}(a_1..a_8) = sum_{k>0} a_k / (2^floor((pk+p)/2)
   k^n), with a_k of period 8, which must appear verbatim (blanks aside); the formulas labelled z3 and z5, each a power
   of two over an integer times zeta(n) on the left and integer multiples of S_{n,p}(a_1..a_8) on the right; the place,
   "the 10,000,000th place"; and the two 64-digit strings of section 4, zeta(3)'s first. Anything else is refused.
2. Digits from the paper's formulas (BBP-type extraction). With zeta(n) = (2^s / D) sum_j c_j S_{n,p_j}(a_j), the
   fractional part of 16^(d-1) zeta(n), whose hexadecimal expansion begins with the digit at place d, is
   sum_j c_j sum_k a_k frac(2^(4(d-1)+s-e_k) / (D k^n)), e_k = floor((p_j k + p_j)/2): for the terms with a non-negative
   exponent the fraction is (2^x mod D k^n) / (D k^n), from Python's modular power; the rest is the convergent tail.
   Each term is truncated to PREC bits, so the sum is within the number of terms (under 2^27) units of its last bit;
   guard_ok checks that the bits below those reported are not within that distance of a carry. The run starts one
   place early, at d - 1, so that the strings at d - 1, d and d + 1 all come from one computation. Two processes share
   the terms in a fixed order.
3. Digits of zeta(3) by an independent series: the Amdeberhan-Zeilberger series, summed exactly by binary splitting in
   GMP (zeta/az.c, compiled in the run), gives zeta(3) to 10,000,081 hexadecimal places and so its digits at every place
   wanted. The paper itself names this comparison. Its guard digits (the 16 after each string) must be neither all 0 nor
   all F.
4. Validation of the extraction on independent values, at places drawn by the seed: SEED_PLACES places uniformly in 1
   to 2,000 (and place 1) for each constant. zeta(3)'s extraction must give the series' digits there, and zeta(5)'s
   must give the digits of Koecher's series, zeta(5) = 2 sum (-1)^(k+1)/(k^5 C(2k,k)) - (5/2) sum (-1)^(k+1)
   H_(k-1)^(2)/(k^3 C(2k,k)), summed here in fixed point with 64 bits to spare.
5. Controls, each of which must fail: zeta(5)'s formula with -738 changed to -737, and zeta(3)'s with its first
   coefficient 6 changed to 5, at the first validation place, must disagree with the independent values; and the
   strings one place before and one place after the 10,000,000th must differ from the paper's (neighbours_differ).
6. Randomness, only from ECDYSIS_SEED: SHA-256(seed || "|" || "zeta/places" || "|" || counter), 8 bytes at a time,
   an integer below n by rejection.

test_passed is 1 if zeta(3)'s 64 digits at the place, from the paper's formula, equal the paper's string and the
series' digits, zeta(5)'s equal its string, the guard and validation hold, and the controls fail; else 0.

What it cannot check:
- zeta(5) by a second method at the ten millionth place: Koecher's series, summed here, checks the extraction code at
  places up to 2,000 only; at the place itself zeta(5)'s digits rest on the paper's formula (z5), which is checked at
  every validation place;
- the formulas' proofs: (z3) and (z5) are identities the paper proves; the run confirms them numerically, at the
  validation places, not by proof.

Writes results/outputs.json (17 values) and results/detail.json.
"""

import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from multiprocessing import Pool

INPUT = ("bbbeta.tex.gz", "6907a4aae3cd1835cc1255355beadd8644ed72bde64de72fda75f624df1b3334", 20146)
PLACE = 10_000_000
NDIG = 64
PREC = 384                     # bits of each term's fixed point: 96 hexadecimal digits, of which 66 are used
SEED_PLACES = 6
MAX_LOW_PLACE = 2000
CHUNK = 1_000_000
S_DEFINITION = r"S_{n,p}(a_1\ldots a_8):=\sum_{k>0}\frac{a_k}{2^{\lfloor\frac{pk+p}{2}\rfloor}k^n}"


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the paper, read (rule 1)

def load(inputs):
    with open(os.path.join(inputs, INPUT[0]), "rb") as f:
        blob = f.read()
    if len(blob) != INPUT[2] or hashlib.sha256(blob).hexdigest() != INPUT[1]:
        raise Refused(f"{INPUT[0]}: not the committed input")
    return gzip.decompress(blob).decode("latin-1")


def squeeze(s):
    return re.sub(r"\s+", "", s)


def formula(tex, label, n):
    """The formula labelled `label`: (two_power, D, [(c, p, (a1..a8))]) with zeta(n) = (two_power / D) sum c S_{n,p}(a)."""
    m = re.search(r"\\begin\{eqnarray\}((?:(?!\\end\{eqnarray\}).)*?)\\label\{" + label + r"\}", tex, re.S)
    if not m:
        raise Refused(f"no formula labelled {label}")
    # the formula is the last row before its label: back to the previous \label or the start of the eqnarray
    body = re.split(r"\\label\{[^}]*\}", m.group(1))[-1]
    body = squeeze(body.replace(r"\nonumber", "").replace(r"\\", "").replace("&&{}", "").replace(r"\,", ""))
    lhs = re.match(r"(?:\\lambda\(\d\)=)?\\dfrac\{?(\d+)\}?\{?(\d+)\}?\\zeta\((\d)\)&=&(.*?)\.?$", body)
    if not lhs:
        raise Refused(f"{label}: the left side is not a fraction times zeta(n): {body[:80]}")
    num, den, nn, rhs = int(lhs.group(1)), int(lhs.group(2)), int(lhs.group(3)), lhs.group(4)
    if nn != n or den & (den - 1):
        raise Refused(f"{label}: zeta({nn}) or denominator {den} not a power of two")
    terms, pos = [], 0
    for t in re.finditer(r"([+-]?)(\d*)S_\{(\d),(\d)\}\(([-\d,]+)\)", rhs):
        if t.start() != pos:
            raise Refused(f"{label}: unparsed text {rhs[pos:t.start()]!r}")
        pos = t.end()
        a = tuple(int(v) for v in t.group(5).split(","))
        if int(t.group(3)) != n or len(a) != 8:
            raise Refused(f"{label}: a term is not S_{{{n},p}} of 8 integers")
        c = int(t.group(2) or "1") * (-1 if t.group(1) == "-" else 1)
        terms.append((c, int(t.group(4)), a))
    if pos != len(rhs) or not terms:
        raise Refused(f"{label}: unparsed text {rhs[pos:]!r}")
    return den.bit_length() - 1, num, terms


def reported(tex):
    """Section 4's place and its two 64-digit strings, zeta(3)'s first."""
    sec = tex.split(r"\section{Computation of digits}")
    if len(sec) != 2:
        raise Refused("no section 'Computation of digits'")
    body = sec[1]
    if "The 64 hexadecimal digits of $\\zeta(3)$ that begin at the\n10,000,000th place" not in body:
        raise Refused("the place is not stated as expected")
    strings = re.findall(r"\{\\tt\s*([0-9A-F]{64})\s*\}\\ldots", body)
    if len(strings) != 2:
        raise Refused(f"expected two 64-digit strings, found {len(strings)}")
    return 10_000_000, strings[0], strings[1]


def paper(tex):
    if squeeze(S_DEFINITION) not in squeeze(tex):
        raise Refused("the definition of S_{n,p} is not as expected")
    return {"z3": formula(tex, "z3", 3), "z5": formula(tex, "z5", 5), "reported": reported(tex)}


# ---------------------------------------------------------------- extraction (rule 2)

def _chunk(args):
    c, p, a, n, D, X, k0, k1, prec = args
    acc, mask = 0, (1 << prec) - 1
    for k in range(k0, k1):
        ak = a[(k - 1) % 8]
        if ak == 0:
            continue
        x = X - (p * k + p) // 2
        if x < 0:
            break
        m = D * k ** n
        acc += c * ak * ((pow(2, x, m) << prec) // m)
    return acc & mask


def frac_bits(f, n, d, prec=PREC, procs=2):
    """floor(frac(16^(d-1) zeta(n)) 2^prec), to within the number of terms, from a formula (s, D, terms)."""
    s, D, terms = f
    X = 4 * (d - 1) + s
    jobs = []
    for c, p, a in terms:
        kmax = (2 * X) // p + 2
        for k0 in range(1, kmax + 1, CHUNK):
            jobs.append((c, p, a, n, D, X, k0, min(k0 + CHUNK, kmax + 1), prec))
    if procs > 1 and len(jobs) > 1:
        with Pool(procs) as pool:
            parts = pool.map(_chunk, jobs, chunksize=1)
    else:
        parts = [_chunk(j) for j in jobs]
    total = sum(parts)
    nterms = sum((2 * X) // p + 2 for _, p, _ in terms)
    for c, p, a in terms:                                  # the tail: exponents below zero, while they matter
        k = max(1, (2 * X) // p - 2)
        while True:
            x = X - (p * k + p) // 2
            if x < 0:
                if prec + x < -40:
                    break
                ak = a[(k - 1) % 8]
                if ak and prec + x >= 0:
                    total += ((c * ak) << (prec + x)) // (D * k ** n)
                nterms += 1
            k += 1
    return total & ((1 << prec) - 1), nterms


def hex_digits(f, n, d, ndig, prec=PREC, procs=2):
    """ndig hexadecimal digits from place d, and whether the bits below are safely away from a carry."""
    v, nterms = frac_bits(f, n, d, prec, procs)
    low_bits = prec - 4 * ndig
    low = v & ((1 << low_bits) - 1)
    safe = nterms < low < (1 << low_bits) - nterms
    return format(v >> low_bits, f"0{ndig}X"), safe


# ---------------------------------------------------------------- independent values (rules 3 and 4)

def build_az(results):
    os.makedirs(os.path.join(results, "build"), exist_ok=True)
    exe = os.path.join(results, "build", "az")
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "az.c")
    subprocess.run(["gcc", "-O2", "-o", exe, src, "-lgmp"], check=True)
    return exe


def az_digits(exe, E, places):
    out = subprocess.run([exe, str(E)] + [str(d) for d in places], check=True, capture_output=True, text=True).stdout
    rows = [line.split() for line in out.strip().split("\n")]
    if len(rows) != len(places):
        raise Refused("az: wrong number of rows")
    return {d: (digits.upper(), guard.upper()) for d, (digits, guard) in zip(places, rows)}


def koecher_zeta5_hex(nhex):
    """zeta(5) to nhex hexadecimal places by Koecher's series, in fixed point with 64 spare bits: '1.' digits."""
    P = 4 * nhex + 64
    one = 1 << P
    s1 = s2 = h2 = 0
    c = 1                                                  # C(2k, k), updated each step
    k = 0
    while True:
        k += 1
        c = c * 2 * (2 * k - 1) // k
        t1 = one // (k ** 5 * c)
        t2 = h2 // (k ** 3 * c)
        if t1 == 0 and t2 == 0:
            break
        if k % 2:
            s1, s2 = s1 + t1, s2 + t2
        else:
            s1, s2 = s1 - t1, s2 - t2
        h2 += one // (k * k)
    z = 2 * s1 - (5 * s2) // 2
    digits = format(z >> 64, "X")
    if len(digits) != nhex + 1 or digits[0] != "1":
        raise Refused("Koecher's series: unexpected expansion")
    return digits, k


def describe(name, n, f):
    """A formula as read, e.g. 'z3: 7/8 zeta(3) = 6 S31 + 4 S33'."""
    s, D, terms = f
    rhs = " ".join(("- " if c < 0 else "+ ") + f"{abs(c)} S{n}{p}" for c, p, _ in terms).lstrip("+ ")
    return f"{name}: {D}/{2 ** s} zeta({n}) = {rhs}"


class Stream:
    """SHA-256(seed || "|" || label || "|" || counter), 8 bytes at a time."""

    def __init__(self, seed_hex, label):
        self.seed, self.label, self.counter, self.buf = bytes.fromhex(seed_hex), label.encode("ascii"), 0, b""

    def below(self, n):
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            if len(self.buf) < 8:
                self.buf += hashlib.sha256(self.seed + b"|" + self.label + b"|" + str(self.counter).encode()).digest()
                self.counter += 1
            x, self.buf = int.from_bytes(self.buf[:8], "big"), self.buf[8:]
            if x < limit:
                return x % n


def low_places(seed):
    st = Stream(seed, "zeta/places")
    return sorted({1} | {1 + st.below(MAX_LOW_PLACE) for _ in range(SEED_PLACES)})


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results", place=None, procs=2, log=print):
    started = time.monotonic()
    tex = load(inputs)
    pp = paper(tex)
    d_paper, s3_paper, s5_paper = pp["reported"]
    d = place or d_paper
    detail = {"formulas": {k: {"two_power": v[0], "D": v[1], "terms": v[2]} for k, v in pp.items() if k != "reported"},
              "place": d, "paper_strings": {"zeta3": s3_paper, "zeta5": s5_paper}}
    exe = build_az(results)

    # Rule 2: both constants from the paper's formulas, from place d - 1.
    ext = {}
    for name, n in (("z3", 3), ("z5", 5)):
        t = time.monotonic()
        digits, safe = hex_digits(pp[name], n, d - 1, NDIG + 2, PREC, procs)
        ext[name] = {"from_d_minus_1": digits, "safe": safe, "seconds": round(time.monotonic() - t, 1)}
        log(f"zeta: {name} from place {d - 1}: {digits} (safe {safe}, {ext[name]['seconds']} s)")
    z3_bbp, z5_bbp = ext["z3"]["from_d_minus_1"][1:1 + NDIG], ext["z5"]["from_d_minus_1"][1:1 + NDIG]

    # Rule 3: zeta(3) by the Amdeberhan-Zeilberger series, at d - 1, d, d + 1 and the validation places.
    lows3 = lows5 = low_places(seed)                              # the same places for both constants
    t = time.monotonic()
    E = d + 1 + NDIG + 16
    az = az_digits(exe, E, [d - 1, d, d + 1] + lows3)
    log(f"zeta: az to {E} places in {time.monotonic() - t:.1f} s")
    z3_az = az[d][0]
    az_guard_ok = all(g not in ("0" * 16, "F" * 16) for _, g in az.values())

    # Rule 4: validation at low places.
    v3 = {p: hex_digits(pp["z3"], 3, p, NDIG, PREC, 1)[0] == az[p][0] for p in lows3}
    k5, kterms = koecher_zeta5_hex(MAX_LOW_PLACE + NDIG + 16)
    v5 = {p: hex_digits(pp["z5"], 5, p, NDIG, PREC, 1)[0] == k5[p:p + NDIG] for p in lows5}
    validation_ok = all(v3.values()) and all(v5.values())

    # Rule 5: controls.
    first = lows3[0]
    s, D, terms = pp["z5"]
    broken5 = (s, D, [(c if c != -738 else -737, p, a) for c, p, a in terms])
    s3_, D3, terms3 = pp["z3"]
    broken3 = (s3_, D3, [(5 if i == 0 else c, p, a) for i, (c, p, a) in enumerate(terms3)])
    controls = {
        "z5_coefficient_changed": hex_digits(broken5, 5, first, NDIG, PREC, 1)[0] != k5[first:first + NDIG],
        "z3_coefficient_changed": hex_digits(broken3, 3, first, NDIG, PREC, 1)[0] != az[first][0],
    }
    neighbours = [ext["z3"]["from_d_minus_1"][0:NDIG], ext["z3"]["from_d_minus_1"][2:2 + NDIG],
                  az[d - 1][0], az[d + 1][0]]
    neighbours5 = [ext["z5"]["from_d_minus_1"][0:NDIG], ext["z5"]["from_d_minus_1"][2:2 + NDIG]]
    neighbours_differ = all(x != s3_paper for x in neighbours) and all(x != s5_paper for x in neighbours5)
    controls["neighbours_differ"] = neighbours_differ

    guard_ok = ext["z3"]["safe"] and ext["z5"]["safe"] and az_guard_ok
    out = {
        "place": d,
        "zeta3_hex_paper_formula": z3_bbp,
        "zeta3_hex_series": z3_az,
        "zeta5_hex_paper_formula": z5_bbp,
        "zeta3_matches_paper": int(z3_bbp == s3_paper),
        "zeta5_matches_paper": int(z5_bbp == s5_paper),
        "zeta3_methods_agree": int(z3_bbp == z3_az),
        "neighbours_differ": int(neighbours_differ),
        "validation_places": ",".join(str(p) for p in lows3),
        "validation_ok": int(validation_ok),
        "koecher_terms": kterms,
        "az_places": E,
        "controls_passed": sum(1 for v in controls.values() if v),
        "controls_total": len(controls),
        "guard_ok": int(guard_ok),
        "formulas": "; ".join(describe(name, n, pp[name]) for name, n in (("z3", 3), ("z5", 5))),
    }
    out["test_passed"] = int(out["zeta3_matches_paper"] and out["zeta5_matches_paper"] and out["zeta3_methods_agree"]
                             and guard_ok and validation_ok and out["controls_passed"] == out["controls_total"]
                             and d == d_paper)
    detail.update({"extraction": ext, "az": {str(k): v for k, v in az.items()}, "validation": {"z3": v3, "z5": v5},
                   "controls": controls, "seconds": round(time.monotonic() - started, 1)})
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"zeta: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
