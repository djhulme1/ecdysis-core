#!/usr/bin/env python3
"""Rabung & Lotts's improved use of cyclic zippers: the 24 new van der Waerden lower bounds of their Table 1, each
certificate rebuilt from its printed prime and checked.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:66ad4a1d0a5682ed) is from Rabung and
Lotts, "Improving the Use of Cyclic Zippers in Finding Lower Bounds for van der Waerden Numbers" (The Electronic
Journal of Combinatorics 19(2), #P35, 2012): "Using this procedure we find some new lower bounds for van der Waerden
numbers."

Its registered test: refuted if, for one of the 24 new lower bounds W(k,l) > n in Table 1, the certificate the paper
builds from its printed prime p, the kth-power classes mod p zipped as marked (Z once, ZZ twice) and joined l - 1
times, holds an l-term arithmetic progression in one colour however the multiples of p are coloured, or p is not a
prime = 1 (mod k); n is read as (l - 1) 2^z p + 1, with z as marked unless another z gives the printed n.

Standard library and the image's gcc (vdw/rl2012.c, compiled here with -O3; vdw/hhlm.py, the line's check of Herwig,
Heule, van Lambalgen and van Maaren's Cyclic Zipper method, imported for its PDF reader, its construction and its
search). The input is the claim's data of record, the paper as the journal serves it (a PDF of 11 pages), checked
against its SHA-256 and size and read in memory as data; nothing in it is run. Every rule below was fixed before any
certificate was built or any progression counted; the PDF's tokens were read first, to transcribe Table 1.

Notation (the paper's): k colours, l the progression length; W(k, l, n) a certificate, a k-colouring of n numbers
with no l-term progression in one colour, so that W(k, l) > n. Numbers are written here as residues, the
certificate's numbers 1..n as 0..n - 1, as the paper does.

1. Reading. The PDF's pages in the order of its page tree, each page's /Resources followed where it is a reference,
   its fonts read from them, its content streams decompressed and tokenised as vdw/hhlm.py does. Table 1 is the run
   of tokens on page 9 from "Table1:" to "SomeoftheentriesinTable1deservecomments:": the header l \\ k 2 3 4 5 6, then
   for l = 3 to 12 the row label and five entries, an entry being an optional ">" (math italic), a number (with "*"
   on W(2, 11)), and, for a new bound, a token "(p)" with "Z" or "ZZ" after it where the paper marks a zipping. The
   parse must equal the transcription TABLE1 below, entry for entry. The paper's statements (STATEMENTS) must be in
   the page texts, spaces removed. The run is refused otherwise.
2. The 24 new bounds: the entries with a prime (W(5,7), W(6,7), W(4,8), W(5,8), W(6,8), W(3,9) to W(6,9), and all
   of W(2..6, l) for l = 10, 11, 12). For each, z is the number of Zs; z_test is the z in 0, 1, 2 with
   (l - 1) 2^z p + 1 equal to the printed n if there is one, else the marked z; the bound tested is
   n_test = (l - 1) 2^z_test p + 1. Each must have p prime, p = 1 (mod k), and k even if z_test >= 1.
3. The construction, for g the least primitive root of p. Classes: x = g^e (mod p) is in C_(e mod k). Unzipped
   (z_test = 0): the numbers 0..(l - 1)p, x coloured by the class of x mod p, the l multiples of p free. Zipped once:
   the paper's arithmetic form of Herwig et al.'s zipping, kappa(y) = class(y mod p) + h [y even] (mod k) on
   Z_2p \\ {0, p}, h = k/2, extended to 0..2(l - 1)p by y -> y mod 2p, the 2l - 1 multiples of p free. This is
   Herwig et al.'s zipped colouring up to the names of the colours when p is point symmetric (m = (p - 1)/k odd) or
   k = 2 (vdw/hhlm.py's turning with the point-symmetric labels; the paper's h = 0 for m even is not Herwig's
   turning, which for k = 2 always swaps the colours); for k >= 4 and m even a zipped entry is not built this way,
   and is undetermined unless rule 5 checks it. Zipped twice (W(4,8) only, p = 85297, a reflection-symmetric
   prime, m even): Herwig et al.'s procedure as vdw/hhlm.py's zip_once performs it, twice, shifting by p each time,
   as the paper says, its turning C_i -> C_(k+1-i) taken under each of the three labellings that differ in it: the
   turning is a fixed-point-free involution of the four classes, and the paper fixes no labelling for a
   reflection-symmetric certificate (the three involutions pair the raw classes 1..4 of vdw/hhlm.py's power_residue
   as 1-4 2-3, the labels of hhlm's rule 2b, as 1-2 3-4, and as 1-3 2-4). The entry holds if one of the three gives
   a certificate that rule 5 finds free of monochromatic progressions; each is reported.
4. The check of an entry with z_test <= 1, by the criterion rl2012.c's crit computes, which is sufficient: (N2) no l
   consecutive residues in [1, p - 1] in one class; (N3) for each i0 in 0..l - 1, the l - 1 nonzero members of the
   string -i0, ..., l - 1 - i0 (mod p) not in one class; and, zipped, (Z3a) no l consecutive numbers of [1, p - 1] or
   [p + 1, 2p - 1] in one kappa-colour, (Z3b) for each place of 0 or of p in an l-string of Z_2p, its other l - 1
   members not in one kappa-colour. Why it suffices: an l-progression a + id with p not dividing d has distinct
   residues mod p (l < p), so at most one multiple of p, and multiplying by d^-1 (mod p, or mod 2p for odd d) maps it
   to an l-string with the colours shifted by class(d), since class and kappa are multiplicative up to that shift
   (kappa(cy) = class(c) + kappa(y) for odd c; an even d keeps the parity, so kappa reduces to class plus a
   constant); one with p | d either holds only multiples of p or (zipped, d = p) alternates parity, and kappa(y + p)
   = kappa(y) + k/2. The multiples of p then take the colours floor(j/2) mod 2 for jp (j mod 2 unzipped), so that no
   progression of them is in one colour. The entry holds if N2, N3 and, zipped, Z3a and Z3b hold. It is refuted
   explicitly if N2 or Z3a fails, as their runs are progressions of difference 1 (or 2, for N2 zipped) avoiding the
   multiples of p in the certificate. If only N3 or Z3b fails it is undetermined (another colouring of the multiples
   might serve).
5. The check of a certificate in full (the double zipping, and the controls): vdw/hhlm.py's check_row with rl2012.c
   as its scanner (forbid and scan for l up to 16): the certificate built by vdw/hhlm.py's build, its free numbers
   (the multiples of p and the added number) coloured by hhlm's search, which finds a colouring that puts no
   progression in one colour through them or shows none exists, then every progression of the certificate scanned.
   For the double zipping, each labelling's certificate is built the same way (the classes relabelled before the
   first zip) and first screened for a progression in one colour among its fixed numbers with difference up to
   SCREEN (rl2012.c first); a labelling with one fails, and the others go through the full check.
6. The test: every one of the 24 holds (rule 4, or 5 for W(4,8)), with rule 2's arithmetic. test_passed is 1 if all
   24 hold; verdict is "refuted" if one is refuted (rule 2's arithmetic failing, an explicit progression, or rule 5
   finding none or no colouring), else "undetermined" if one is, else "confirmed".
7. Beside, not counted: each printed n against (l - 1) 2^z p + 1 for its mark; W(4,9) zipped as marked, the bound
   that would give; Table 1's other 26 entries (bounds known before the paper, and exact values); and the comments'
   statements.

Controls (controls_passed counts those that behave as stated): (a) for 300 residues per entry drawn from the seed,
crit's class is the one Euler's criterion gives, x^((p - 1)/k) = (g^((p - 1)/k))^class (mod p), and N3 and Z3b
recounted by that criterion agree with crit's; (b) the four smallest single entries, W(2,10), W(2,11) Z, W(2,12) Z
and W(3,9), checked in full by rule 5 agree with rule 4; (c) rule 3's colourings equal vdw/hhlm.py's builds up to
the names of the colours, unzipped for W(2,10) and W(3,9) and zipped for 9697, 29033, 622159 and 1362341 (k = 2, 2,
6 and 4); (d) on 40 seed-drawn small cases (k in 2, 3, 4, 6; l in 3 to 6; a prime p = 1 mod k from 101 to 3000; zipped
when k = 2 or (p - 1)/k is odd, otherwise not) and the twelve rows of Herwig et al.'s Table 3 with z <= 1
(vdw/hhlm.py's TABLE3, whose certificates the line's receipt on that paper checked in full), rule 4's holding
implies rule 5's and its explicit refutation implies rule 5's failing; (e) rl2012.c's scan agrees with a direct enumeration in Python on
30 seed-drawn colourings (lengths 20 to 120, 2 to 4 colours, l from 3 to 8, some numbers free), and finds a
progression planted at a seed-drawn place in the W(2,10) certificate.

Changed after the trial (15 October; the rules were first committed at 17f39c5). A trial in the reference runner,
under a seed of Imago's own, built the double-zipped W(4,8) certificate with vdw/hhlm.py's build alone, that is
with the turning of hhlm's rule 2b labels (raw classes 1-4 and 2-3 swapped), and its full scan found 32,241,888
8-term progressions in one colour among 407,431,526,734, the first eight consecutive numbers from 17,678; the other
23 entries held by the criterion, and all five controls passed. hhlm's labels are its reading of Herwig et al. for
their certificates, every one of which with four or more colours that it zips is point symmetric; for a
reflection-symmetric certificate the paper's own text fixes no labelling (its arithmetic turning, a shift by h = 0
when m is even, is no turning at all, and with it its k = 2 entries, both reflection symmetric, would hold
progressions of difference p, while with Herwig's swap they hold). So the double zipping is now taken under each of
the three labellings that differ in the turning (rule 3), the first trial's being the first of them, and rule 5 and
the outputs say which hold. This change was made after the trial's outcome was seen.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 vdw/rl2012.py
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("vdw_hhlm", os.path.join(HERE, "hhlm.py"))
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)

INPUT = ("rabung-lotts-ejc-19-2-p35.pdf", "dbeddaf95f8e82acfb02bdfec0a153c36c114ddfd46ff84924287b026016d541", 304111)
PAGES = 11
TABLE_PAGE = 9
LIMIT = 200
FREE = 255
CHI_SAMPLES = 300
SCREEN = 3000
# Rule 3: the three turnings of the double zipping, as relabellings of hhlm's raw classes before the first zip,
# chosen so that hhlm's turning (label i -> 5 - i) swaps the pairs named.
TURNINGS = (("1-4 2-3", {1: 1, 2: 2, 3: 3, 4: 4}), ("1-2 3-4", {1: 1, 2: 4, 3: 2, 4: 3}),
            ("1-3 2-4", {1: 1, 2: 2, 3: 4, 4: 3}))
RANDOM_CASES = 40
SCAN_CONTROLS = 30
STATEMENTS = (
    "Using this procedure we find some new lower bounds for van der Waerden numbers.",
    "We applied this procedure to all primes less than 10,000,000",
    "There is only one double zipping reported in this table.",
    "We have not found a shortcut for verifying that a k-coloring resulting from a double zipping is "
    "l-progression free.",
)
# Table 1 as printed: for l = 3..12, the entries for k = 2..6: (strict ">", value, star, prime or None, mark).
TABLE1 = {
    3: ((False, 9, False, None, ""), (False, 27, False, None, ""), (False, 76, False, None, ""),
        (True, 170, False, None, ""), (True, 223, False, None, "")),
    4: ((False, 35, False, None, ""), (True, 292, False, None, ""), (True, 1048, False, None, ""),
        (True, 2254, False, None, ""), (True, 9778, False, None, "")),
    5: ((False, 178, False, None, ""), (True, 2173, False, None, ""), (True, 17705, False, None, ""),
        (True, 98740, False, None, ""), (True, 98740, False, None, "")),
    6: ((False, 1132, False, None, ""), (True, 11191, False, None, ""), (True, 91331, False, None, ""),
        (True, 540025, False, None, ""), (True, 816981, False, None, "")),
    7: ((True, 3703, False, None, ""), (True, 48811, False, None, ""), (True, 420217, False, None, ""),
        (True, 1381687, False, 230281, ""), (False, 7465909, False, 622159, "Z")),
    8: ((True, 11495, False, None, ""), (True, 238400, False, None, ""), (True, 2388317, False, 85297, "ZZ"),
        (True, 10743258, False, 1534751, ""), (True, 57445718, False, 8206531, "")),
    9: ((True, 41265, False, None, ""), (True, 932745, False, 116593, ""), (True, 10898729, False, 1362341, "Z"),
        (True, 79706009, False, 9963251, ""), (True, 159986609, False, 9999163, "Z")),
    10: ((True, 103474, False, 11497, ""), (True, 4173724, False, 463747, ""), (True, 760492218, False, 8449913, ""),
         (True, 89999920, False, 9999991, ""), (True, 179998975, False, 9999943, "Z")),
    11: ((True, 193941, True, 9697, "Z"), (True, 18603731, False, 1860373, ""), (True, 198841541, False, 9942077, "Z"),
         (True, 99999711, False, 9999971, ""), (True, 199998621, False, 9999931, "Z")),
    12: ((True, 638727, False, 29033, "Z"), (True, 79134144, False, 7194013, ""),
         (True, 219988319, False, 9999469, "Z"), (True, 109999242, False, 9999931, ""),
         (True, 219996107, False, 9999823, "Z")),
}
DIRECT = ((2, 10), (2, 11), (2, 12), (3, 9))
ZIP_FORMS = (9697, 29033, 622159, 1362341)
KNOWN = tuple((r, k, p, z) for r, k, p, z, n, bold in H.TABLE3 if z <= 1)
OUTPUTS = ("statements", "table", "entries_held", "entries_total", "criterion", "double_zip", "largest", "printed_n",
           "w49_zipped", "known_entries", "chi", "direct", "closed_form", "random_cases", "scans", "verdict",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ----------------------------------------------------------------------------------------------------------- reading

def read_input(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


class Pdf(H.Pdf):
    """vdw/hhlm.py's reader, with each page's /Resources followed where it is a reference."""

    def page(self, num, body):
        cont = re.search(rb"/Contents\s*(\[[^\]]*\]|\d+\s+0\s+R)", body)
        if not cont:
            raise Refused(f"page {num} has no /Contents")
        streams = [int(x) for x in re.findall(rb"(\d+)\s+0\s+R", cont.group(1))]
        res = re.search(rb"/Resources\s*(<<.*?>>|\d+\s+0\s+R)", body, re.S)
        if not res:
            raise Refused(f"page {num} has no /Resources")
        rtext = res.group(1)
        if not rtext.startswith(b"<<"):
            rtext = self.body(int(rtext.split()[0]))
        fonts = {}
        font = re.search(rb"/Font\s*(<<.*?>>|\d+\s+0\s+R)", rtext, re.S)
        if font:
            text = font.group(1)
            refs = self.dict_refs(text) if text.startswith(b"<<") else self.dict_refs(self.body(int(text.split()[0])))
            for name, obj in refs.items():
                base = re.search(rb"/BaseFont\s*/([^\s/<>\[\]]+)", self.body(obj))
                if not base:
                    raise Refused(f"font {name} (object {obj}) has no /BaseFont")
                fonts[name] = base.group(1).decode("latin-1")
        content = b"\n".join(self.stream(s) for s in streams)
        return content, fonts


def document(data):
    pages = Pdf(data).pages()
    if len(pages) != PAGES:
        raise Refused(f"{len(pages)} pages, not {PAGES}")
    return [H.page_tokens(content, fonts) for content, fonts in pages]


def statements_found(pages):
    texts = [H.page_text(t) for t in pages]
    return {s: any(s.replace(" ", "") in t for t in texts) for s in STATEMENTS}


def parse_table(tokens):
    """Rule 1: Table 1's rows from the page's tokens, as {l: (entries...)}."""
    texts = [t for t, _ in tokens]
    try:
        start = texts.index("Table1:")
        stop = texts.index("SomeoftheentriesinTable1deservecomments:", start)
    except ValueError:
        raise Refused("Table 1 is not on its page")
    toks = tokens[start + 1:stop]
    i = 0
    while i < len(toks) and not (toks[i][0] == "l" and H.family(toks[i][1]) == "CMTI"):
        i += 1
    head = [t for t, _ in toks[i:i + 8]]
    if head != ["l", "n", "k", "2", "3", "4", "5", "6"]:
        raise Refused(f"Table 1's header reads {head}")
    i += 8
    rows = {}
    for l in range(3, 13):
        if i >= len(toks) or toks[i][0] != str(l):
            raise Refused(f"Table 1: no row {l} where expected")
        i += 1
        entries = []
        for _ in range(5):
            strict = False
            if i < len(toks) and toks[i][0] == ">" and H.family(toks[i][1]) == "CMMI":
                strict, i = True, i + 1
            m = re.fullmatch(r"(\d+)(\*?)", toks[i][0]) if i < len(toks) else None
            if not m:
                raise Refused(f"Table 1, row {l}: {toks[i][0] if i < len(toks) else None!r} is not a number")
            value, star = int(m.group(1)), bool(m.group(2))
            i += 1
            prime, mark = None, ""
            if i < len(toks):
                pm = re.fullmatch(r"\((\d+)\)(Z{0,2})", toks[i][0])
                if pm:
                    prime, mark, i = int(pm.group(1)), pm.group(2), i + 1
            entries.append((strict, value, star, prime, mark))
        rows[l] = tuple(entries)
    if i != len(toks):
        raise Refused(f"Table 1: {len(toks) - i} tokens after row 12")
    return rows


def new_bounds(rows):
    """Rule 2: the entries with a prime, as (k, l, p, mark, printed n)."""
    out = []
    for l, entries in rows.items():
        for k, (strict, value, star, prime, mark) in zip(range(2, 7), entries):
            if prime is not None:
                out.append((k, l, prime, mark, value))
    return out


def z_for(l, p, mark, printed):
    """Rule 2: the z tested, and the bound it gives."""
    hits = [z for z in (0, 1, 2) if (l - 1) * 2 ** z * p + 1 == printed]
    z = hits[0] if len(hits) == 1 else len(mark)
    return z, (l - 1) * 2 ** z * p + 1


# ------------------------------------------------------------------------------------------------------- arithmetic

def compile_c(work):
    exe = os.path.join(work, "rl2012")
    subprocess.run(["gcc", "-O3", "-std=gnu11", "-pthread", "-o", exe, os.path.join(HERE, "rl2012.c")], check=True)
    return exe


def crit(exe, k, l, p, z, g, samples=()):
    """rl2012.c crit; with samples, also the classes of those residues, read from rl2012.c's kappa file (z = 0)."""
    out = subprocess.run([exe, "crit", str(k), str(l), str(p), str(z), str(g)], check=True, capture_output=True,
                         text=True).stdout.split()
    keys = ("cover", "n2_run", "n2_at", "n3_bad", "n3_first", "z3a_run", "z3a_at", "z3b_bad", "z3b_first")
    res = dict(zip(keys, map(int, out[:9])))
    if samples:
        path = os.path.join(os.path.dirname(exe), f"kappa-{k}-{p}-0.bin")
        subprocess.run([exe, "kappa", str(k), str(p), str(g), "0", path], check=True)
        with open(path, "rb") as fh:
            res["sampled"] = {}
            for x in samples:
                fh.seek(x)
                res["sampled"][x] = fh.read(1)[0]
        os.remove(path)
    return res


def verdict_of(res, z):
    """Rule 4: 'holds', 'refuted' (an explicit progression) or 'undetermined'."""
    if not res["cover"]:
        return "refuted"
    if res["n2_at"] or (z == 1 and res["z3a_at"]):
        return "refuted"
    if res["n3_bad"] or (z == 1 and res["z3b_bad"]):
        return "undetermined"
    return "holds"


def chi_check(k, l, p, z, g, res, samples):
    """Control (a): crit's classes and its N3 and Z3b counts by Euler's criterion."""
    e = (p - 1) // k
    omega = pow(g, e, p)
    powers = [pow(omega, c, p) for c in range(k)]
    sampled_ok = all(pow(x, e, p) == powers[res["sampled"][x]] for x in samples)

    def chi(y):
        return pow(y % p, e, p)

    n3 = 0
    for i0 in range(l):
        vals = {chi((i - i0) % p) for i in range(l) if i != i0}
        n3 += len(vals) == 1
    ok = sampled_ok and n3 == res["n3_bad"]
    z3b = None
    if z == 1:
        m = 2 * p

        def psi(y):
            y %= m
            return chi(y) * (p - 1 if y % 2 == 0 else 1) % p
        z3b = 0
        for centre in (0, p):
            for i0 in range(l):
                vals = {psi(centre + i - i0) for i in range(l) if i != i0}
                z3b += len(vals) == 1
        ok = ok and z3b == res["z3b_bad"]
    return ok, {"sampled_ok": sampled_ok, "n3": n3, "z3b": z3b}


def closed_form_matches(exe, work, k, l, p, z, g):
    """Control (c): rule 3's colouring of 1..2^z p against vdw/hhlm.py's build, up to the names of the colours."""
    path = os.path.join(work, f"kappa-{k}-{p}-{z}.bin")
    subprocess.run([exe, "kappa", str(k), str(p), str(g), str(z), path], check=True)
    with open(path, "rb") as fh:
        mine = fh.read()
    os.remove(path)
    cert, free, N = H.build(k, l, p, z, g)
    if N != len(mine):
        return False
    names = {}
    for y in range(N):
        if free[y] != (mine[y] == FREE):
            return False
        if free[y]:
            continue
        if names.setdefault(mine[y], cert[y]) != cert[y]:
            return False
    return len(set(names.values())) == len(names) == k


def build_labelled(k, l, p, z, rho, labels):
    """vdw/hhlm.py's build, the raw classes relabelled before zipping (rule 3, the double zipping)."""
    col, free = H.power_residue(p, k, rho)
    col = [labels[c] for c in col]
    for _ in range(z):
        col, free = H.zip_once(col, free, k, p)
    N = len(col)
    n = (l - 1) * N + 1
    cert = [col[(y - 1) % N] for y in range(1, n)] + [k]
    fr = [free[(y - 1) % N] for y in range(1, n)] + [True]
    return cert, fr, N


def c_first(exe, path, l, dmax):
    out = subprocess.run([exe, "first", path, str(l), str(dmax)], check=True, capture_output=True,
                         text=True).stdout.split()
    x, d = map(int, out)
    return (x, d) if d else None


def double_zip(exe, work, k, l, p, rho):
    """Rules 3 and 5 for the double zipping: each turning screened, and checked in full unless the screen fails."""
    n = (l - 1) * 4 * p + 1
    out = []
    for name, labels in TURNINGS:
        cert, free, N = build_labelled(k, l, p, 2, rho, labels)
        free_pos = [y for y in range(1, len(cert) + 1) if free[y - 1]]
        row = {"turning": name, "n": len(cert), "length_ok": len(cert) == n,
               "free_as_stated": free_pos == [1 + j * p for j in range((l - 1) * 4 + 1)]}
        path = os.path.join(work, "zz.bin")
        H.write_colouring(path, cert, free)
        first = c_first(exe, path, l, SCREEN)
        row["screen"] = list(first) if first else None
        if first or not row["free_as_stated"]:
            row.update({"holds": False, "found": None, "scan": None})
            os.remove(path)
            out.append(row)
            continue
        forbidden, multi = H.c_forbid(exe, path, l)
        if multi:
            raise Refused(f"W({k},{l}) {name}: {multi} progressions hold two free numbers and a fixed one")
        forb = {y: set(w) for y, w in forbidden.items()}
        progs = H.free_progressions(free_pos, len(cert), l)
        own = [cert[y - 1] for y in free_pos]
        assign, nodes = H.search(free_pos, forb, own, progs, k)
        row.update({"found": assign is not None, "nodes": nodes})
        if assign is None:
            row.update({"holds": False, "scan": None})
        else:
            final = list(cert)
            for y, c in zip(free_pos, assign):
                final[y - 1] = c
            H.write_colouring(path, final)
            sc = H.c_scan(exe, path, l)
            row.update({"scan": sc, "holds": row["length_ok"] and sc["count"] == 0})
        os.remove(path)
        out.append(row)
    return out


def full_check(exe, work, k, l, p, z, g):
    """Rule 5: vdw/hhlm.py's check_row with rl2012.c's forbid and scan."""
    n = (l - 1) * 2 ** z * p + 1
    row, _ = H.check_row(exe, work, k, l, p, z, n, g)
    for f in os.listdir(work):
        if f.endswith(".bin"):
            os.remove(os.path.join(work, f))
    return row


# ---------------------------------------------------------------------------------------------------------- controls

def random_prime(st, k):
    while True:
        p = 101 + st.below(2900)
        if H.is_prime(p) and (p - 1) % k == 0:
            return p


def random_cases(exe, work, seed):
    st = H.Stream(seed, "cases")
    cases = []
    for _ in range(RANDOM_CASES):
        k = (2, 3, 4, 6)[st.below(4)]
        l = 3 + st.below(4)
        p = random_prime(st, k)
        z = 1 if k % 2 == 0 and (k == 2 or ((p - 1) // k) % 2 == 1) else 0
        cases.append((k, l, p, z))
    cases += [tuple(c) for c in KNOWN]
    out, ok = [], True
    for k, l, p, z in cases:
        g = H.least_primitive_root(p)
        v = verdict_of(crit(exe, k, l, p, z, g), z)
        row = full_check(exe, work, k, l, p, z, g)
        agree = (v != "holds" or row["holds"]) and (v != "refuted" or not row["holds"])
        ok = ok and agree
        out.append({"k": k, "l": l, "p": p, "z": z, "criterion": v, "full": row["holds"], "agree": agree})
    return ok, out


def scan_controls(exe, work, seed):
    st = H.Stream(seed, "scans")
    ok = True
    for i in range(SCAN_CONTROLS):
        n = 20 + st.below(101)
        r = 2 + st.below(3)
        l = 3 + st.below(6)
        cert, free = H.random_colouring(st, n, r, st.below(3))
        path = os.path.join(work, f"scan{i}.bin")
        H.write_colouring(path, cert, free)
        got = H.c_scan(exe, path, l)
        want, pairs = H.py_scan(cert, free, l)
        ok = ok and got["count"] == want and got["pairs"] == pairs
        os.remove(path)
    return ok


def planted(exe, work, seed, g):
    """Control (e): a progression planted in the W(2,10) certificate is found."""
    st = H.Stream(seed, "plant")
    k, l, p, z = 2, 10, 11497, 0
    cert, free, N = H.build(k, l, p, z, g)
    n = len(cert)
    while True:
        d = 1 + st.below(n // (l - 1) - 1)
        x = st.below(n - (l - 1) * d)
        ys = [x + t * d for t in range(l)]
        if not any(free[y] for y in ys):
            break
    for y in ys:
        cert[y] = cert[ys[0]]
    path = os.path.join(work, "planted.bin")
    H.write_colouring(path, cert, free)
    got = H.c_scan(exe, path, l)
    os.remove(path)
    return got["count"] >= 1, {"x": x + 1, "d": d}


# ----------------------------------------------------------------------------------------------------------- the run

def assess(rows, stmts, exe, work, seed):
    bounds = new_bounds(rows)
    entries, roots = [], {}
    chi_ok = True
    st = H.Stream(seed, "chi")
    for k, l, p, mark, printed in bounds:
        z, n_test = z_for(l, p, mark, printed)
        e = {"k": k, "l": l, "p": p, "mark": mark, "printed": printed, "z": z, "n": n_test,
             "printed_matches": (l - 1) * 2 ** len(mark) * p + 1 == printed}
        arith = H.is_prime(p) and (p - 1) % k == 0 and (z == 0 or k % 2 == 0)
        e["arithmetic"] = arith
        if not arith:
            e["verdict"] = "refuted"
            entries.append(e)
            continue
        g = H.least_primitive_root(p)
        roots[p] = g
        m = (p - 1) // k
        e["g"], e["point_symmetric"] = g, (k % 2 == 0 and m % 2 == 1)
        if z <= 1:
            if z == 1 and not (k == 2 or m % 2 == 1):
                e["verdict"] = "undetermined"
            else:
                samples = sorted({1 + st.below(p - 1) for _ in range(CHI_SAMPLES)})
                res = crit(exe, k, l, p, z, g, samples)
                ok, info = chi_check(k, l, p, z, g, res, samples)
                chi_ok = chi_ok and ok
                res.pop("sampled", None)
                e.update({"crit": res, "chi": info, "verdict": verdict_of(res, z)})
        else:
            rows_zz = double_zip(exe, work, k, l, p, g)
            e["turnings"] = rows_zz
            e["verdict"] = "holds" if any(r["holds"] for r in rows_zz) else "refuted"
        entries.append(e)

    # beside: W(4,9) zipped as marked
    w49 = next(e for e in entries if (e["k"], e["l"]) == (4, 9))
    res49 = crit(exe, 4, 9, w49["p"], 1, roots[w49["p"]]) if w49["p"] in roots else None
    w49_verdict = verdict_of(res49, 1) if res49 else "not built"

    # controls
    controls = {"chi": chi_ok}
    direct = []
    for k, l in DIRECT:
        e = next(x for x in entries if (x["k"], x["l"]) == (k, l))
        if "g" not in e:
            direct.append({"k": k, "l": l, "p": e["p"], "z": e["z"], "criterion": e["verdict"], "full": False,
                           "progressions": None})
            continue
        row = full_check(exe, work, k, l, e["p"], e["z"], e["g"])
        direct.append({"k": k, "l": l, "p": e["p"], "z": e["z"], "criterion": e["verdict"], "full": row["holds"],
                       "progressions": row["scan"]["pairs"] if row.get("scan") else None})
    controls["direct"] = all((d["criterion"] == "holds") == d["full"] for d in direct)
    forms = []
    for k, l in ((2, 10), (3, 9)):
        e = next(x for x in entries if (x["k"], x["l"]) == (k, l))
        forms.append("g" in e and closed_form_matches(exe, work, k, l, e["p"], 0, e["g"]))
    for p in ZIP_FORMS:
        e = next(x for x in entries if x["p"] == p)
        forms.append("g" in e and closed_form_matches(exe, work, e["k"], e["l"], p, 1, e["g"]))
    controls["closed_form"] = all(forms)
    rc_ok, rc = random_cases(exe, work, seed)
    controls["random_cases"] = rc_ok
    sc_ok = scan_controls(exe, work, seed)
    pl_ok, pl = planted(exe, work, seed, roots[11497]) if 11497 in roots else (False, None)
    controls["scans"] = sc_ok and pl_ok

    held = [e for e in entries if e["verdict"] == "holds"]
    refuted = [e for e in entries if e["verdict"] == "refuted"]
    undet = [e for e in entries if e["verdict"] == "undetermined"]
    cond = {"24 new bounds read": len(entries) == 24,
            "each with p prime, p = 1 (mod k), k even if zipped": all(e["arithmetic"] for e in entries),
            "each certificate holds": len(held) == len(entries)}
    verdict = "refuted" if refuted else ("undetermined" if undet else "confirmed")
    by_crit = [e for e in entries if "crit" in e]
    zz = next(e for e in entries if e["z"] == 2)
    largest = max(entries, key=lambda e: e["n"])
    mism = [e for e in entries if not e["printed_matches"]]
    rest = [(l, k) for l, row in rows.items() for k, ent in zip(range(2, 7), row) if ent[3] is None]

    def name(e):
        return f"W({e['k']},{e['l']})"
    values = {
        "statements": f"{sum(stmts.values())} of {len(stmts)} statements found",
        "table": (f"Table 1 read: {sum(len(v) for v in rows.values())} entries, {len(entries)} with a prime "
                  f"({sum(e['mark'] == 'Z' for e in entries)} Z, {sum(e['mark'] == 'ZZ' for e in entries)} ZZ)"),
        "entries_held": len(held),
        "entries_total": len(entries),
        "criterion": (f"{sum(e['verdict'] == 'holds' for e in by_crit)} of {len(by_crit)} by the criterion hold"
                      + (f"; refuted: {', '.join(name(e) for e in refuted)}" if refuted else "")
                      + (f"; undetermined: {', '.join(name(e) for e in undet)}" if undet else ""))[:LIMIT],
        "double_zip": (f"W(4,8) > {zz['n']} ({zz['p']}, ZZ), by turning: " + "; ".join(
            f"{r['turning']} " + ("holds" if r["holds"] else (
                f"fails, from {r['screen'][0]} by {r['screen'][1]}" if r.get("screen") else (
                    f"fails, {r['scan']['count']} in one colour" if r.get("scan") else "no colouring")))
            for r in zz.get("turnings", [])))[:LIMIT],
        "largest": f"{name(largest)} > {largest['n']} ({largest['p']}, {largest['mark'] or 'unzipped'}): "
                   f"{largest['verdict']}",
        "printed_n": (f"{len(entries) - len(mism)} of {len(entries)} printed bounds are (l - 1)2^z p + 1 for their "
                      f"mark; not: " + "; ".join(f"{name(e)} {e['mark'] or 'unmarked'} printed {e['printed']}, the "
                                                   f"prime gives {(e['l'] - 1) * 2 ** len(e['mark']) * e['p'] + 1}"
                                                   for e in mism))[:LIMIT],
        "w49_zipped": f"W(4,9) zipped as marked, > {(9 - 1) * 2 * w49['p'] + 1}: {w49_verdict}",
        "known_entries": f"{len(rest)} entries without a prime (known before the paper), not tested",
        "chi": f"{CHI_SAMPLES} residues an entry and the N3 and Z3b strings by Euler's criterion: "
               f"{'agree' if chi_ok else 'disagree'}",
        "direct": "; ".join(f"W({d['k']},{d['l']}) full {'holds' if d['full'] else 'fails'}, criterion "
                            f"{d['criterion']}" for d in direct)[:LIMIT],
        "closed_form": f"{sum(forms)} of {len(forms)} colourings equal vdw/hhlm.py's builds up to names",
        "random_cases": (f"{sum(c['agree'] for c in rc)} of {len(rc)} cases agree (criterion holds "
                         f"{sum(c['criterion'] == 'holds' for c in rc)}, refuted "
                         f"{sum(c['criterion'] == 'refuted' for c in rc)}; full holds {sum(c['full'] for c in rc)})"),
        "scans": f"{SCAN_CONTROLS} scans against enumeration {'agree' if sc_ok else 'disagree'}; planted progression "
                 f"{'found' if pl_ok else 'missed'}",
        "verdict": verdict,
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"conditions": cond, "controls": controls, "statements": stmts, "entries": entries,
              "w49_zipped": res49, "direct": direct, "closed_form": forms, "random_cases": rc, "planted": pl,
              "roots": roots, "known_entries": rest}
    return out, detail


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    data = read_input(inputs)
    pages = document(data)
    stmts = statements_found(pages)
    rows = parse_table(pages[TABLE_PAGE - 1])
    if rows != TABLE1:
        raise Refused("Table 1 as read differs from its transcription")
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)
    try:
        exe = compile_c(work)
        out, detail = assess(rows, stmts, exe, work, seed)
    finally:
        shutil.rmtree(work, ignore_errors=True)
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
    except (Refused, H.Refused) as e:
        sys.exit(f"rl2012: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
