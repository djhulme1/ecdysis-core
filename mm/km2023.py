#!/usr/bin/env python3
"""Kauers & Moosbauer (2023): new schemes for multiplying an n x m matrix by an m x 6 matrix, 2 <= n, m <= 6.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from M. Kauers and J. Moosbauer, "Some New
Non-Commutative Matrix Multiplication Algorithms of Size (n,m,6)" (arXiv:2306.00882v1, 1 June 2023): "For various
$2\\leq n,m \\leq 6$, we propose some new algorithms for multiplying an $n\\times m$ matrix with an $m \\times 6$
matrix over a possibly noncommutative coefficient ring."

The test, as registered: see TEST below. Standard library only (the python image), no network: every input is read
from inputs/<name> after its SHA-256 is checked against the claim's data of record. The checks of a scheme are
mm/check.py's (imported, not changed). Every rule below was fixed before any scheme was read for an outcome.

1. The paper's convention (its Section 2): the matrix multiplication tensor of format (n, m, p) is
   sum_{i,j,k} a_{i,j} (x) b_{j,k} (x) c_{k,i} in K^{n x m} (x) K^{m x p} (x) K^{p x n}, and a scheme of rank R
   writes it as R terms M1 (x) M2 (x) M3 with M1 n x m, M2 m x p and M3 p x n. mm/check.py indexes the same way:
   u by i*m + j, v by j*p + k, w by k*n + i (the entry of M3 in row k and column i).
2. The printed schemes. The e-print's TeX (main.tex in its source archive km2023-src.tar.gz, read in memory and
   never unpacked to disk) prints in its Appendix one scheme of rank 56 for (2,6,6) and one for (3,4,6), each term
   as \\begin{pmatrix}..\\end{pmatrix}\\otimes\\begin{pmatrix}..\\end{pmatrix}\\otimes\\begin{pmatrix}..\\end{pmatrix},
   the terms joined by +, each entry a number k or \\bar k for -k ("minus signs are placed above numbers rather than
   in front of them"). The reader takes the alignat* block after "Here is one of our schemes of rank 56 for the
   format $(n,m,p)$", reads its pmatrix environments in order, three to a term, and refuses a block whose matrices
   do not come in triples of the format's shapes (n x m, m x p, p x n), whose matrices within a term are not joined
   by \\otimes alone, whose terms are not joined by a + (with the alignment's & and line breaks \\\\ around it), or
   whose entries are anything else. A scheme exact over the integers is valid over every ring, a noncommutative one
   included: its products are linear forms in the a's times linear forms in the b's, with integer coefficients.
3. The released schemes. The 15 files solutions/<n><m><p>-<rank>-mod2.exp of jakobmoosbauer/flips at e2fa414 (the
   commit "nm6 schemes", 1 June 2023, the e-print's date), which the e-print names ("schemes for other formats
   (n,m,6) over K = Z_2 are available at https://github.com/jakobmoosbauer/flips.git"), one product per line in
   Kauers & Moosbauer's .exp format, read by mm/check.py's read_flips and checked modulo 2. A file's products are
   its non-empty lines, every one of which must read as a product of three linear forms. The table's rank for each
   format, as the e-print's table prints it ("our rank"): (2,2,6) 21, (2,3,6) 30, (2,4,6) 39, (3,3,6) 42, (2,5,6)
   48, (3,4,6) 56, (2,6,6) 56, (3,5,6) 71, (4,4,6) 74, (3,6,6) 85, (4,5,6) 93, (4,6,6) 116, (5,5,6) 116, (5,6,6)
   144, (6,6,6) 164; the rank in each file's name is reported beside.
4. Hopcroft and Kerr's count for multiplying a p x 2 by a 2 x n matrix, ceil((3pn + max(n, p))/2) (the abstract of
   their 1971 paper, which the e-print cites for the family of (2,m,p) schemes it improves), taken for (6,2,6):
   (2,6,6) and (6,2,6) have the same rank, a scheme for one being a scheme for the other with its three factors
   moved round (u, v, w to v, w, u) and the formats likewise.
5. The test's four conditions: (1) the printed (2,6,6) scheme has 56 terms and is exact over the integers; (2) the
   printed (3,4,6) scheme has 56 terms and is exact over the integers; (3) every one of the 15 released files is
   exact modulo 2 and has at most its format's table rank of products; (4) the Hopcroft-Kerr count for (6,2,6) is
   above 56. test_passed is 1 if all four hold.
6. Beside the test, none of it counted: each file's products against the rank in its name; three products of
   matrices drawn from the seed computed by every scheme against the schoolbook product (mm/check.py's probe, its
   digest an output); the printed schemes' terms with a coefficient other than 0, 1 and -1.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): the paper's own examples
in its Section 2, read by a reader of their notation ("(a_{1,1} + a_{2,2}) \\otimes (b_{1,1} + b_{2,2}) \\otimes
(c_{1,1}+c_{2,2})"): the standard algorithm, 8 terms, and Strassen's, 7, are exact over the integers, and Strassen's
with c_{k,i} read as the entry (i, k) is not; mm/check.py's own self-test (Strassen's scheme and broken copies of it)
passes; and for every printed scheme and released file, one coefficient of one term increased by one, both drawn
from the seed, makes exactly |v_r| x |w_r| entries wrong.

Seen before the rules were written: the e-print (its text, table, remarks and the appendix's TeX syntax: the
separators between its matrices and the shapes of its entries, no scheme read or counted); and git's summary of the
commit e2fa414, which lists each file's line count (366-85-mod2.exp, for the table's 85, has 86 lines). No released
file was opened before the rules were committed.

What it cannot check: whether each rank was the best known (the table's "best rank" is Sedoglavic's catalogue as the
paper read it); the integer versions of other formats added to the repository later (commit 65ed0dc, 26 June 2023),
which the e-print does not name; how the flip graph search found the schemes.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 mm/km2023.py
"""

import importlib.util
import io
import json
import os
import re
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_check", os.path.join(HERE, "check.py"))
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

TEST = ("Refuted if either scheme the appendix prints, (2,6,6) and (3,4,6) with 56 products each (bars for minus "
        "signs), is not an exact decomposition of its matrix multiplication tensor over the integers in the paper's "
        "convention (a_ij ⊗ b_jk ⊗ c_ki), and so not valid over a noncommutative ring; if a scheme the authors "
        "released for one of the table's 15 formats (n,m,6) (jakobmoosbauer/flips at e2fa414) is not exact modulo 2 "
        "or has more products than the table's rank; or if Hopcroft and Kerr's ⌈(3pn + max(n,p))/2⌉ for (6,2,6) is "
        "not above 56.")

SOURCE = ("km2023-src.tar.gz", "40ee1623eb8c5bd2a754ae2dbd985e2b76dae90ccd38414b800cfa8b47b8af2f")
PRINTED = (((2, 6, 6), 56), ((3, 4, 6), 56))
# the table's formats and ranks ("our rank"), each with its released file and its SHA-256
RELEASED = (
    ((2, 2, 6), 21, "flips-226-21-mod2.exp", "fb2e23a6000f4cea0edbd45e1f4a3945dc25f91a479c3d04ff314c6b4dc855e6"),
    ((2, 3, 6), 30, "flips-236-30-mod2.exp", "791c70a4a57188b5c0d5776be6966d8d17c0872d2b8fff1fd8700f2e210bf192"),
    ((2, 4, 6), 39, "flips-246-39-mod2.exp", "8a701a6fcd7e86a859c36d4a198809a1b8777da9b89d3afd3856022520ad99fd"),
    ((3, 3, 6), 42, "flips-336-42-mod2.exp", "7a139d20af254324306a374ae99ab1ae73d0ce62fc2c509be96355629e09e345"),
    ((2, 5, 6), 48, "flips-256-48-mod2.exp", "5bb6a9881ef38d82094714759722f0be8140cba588441e328a60b3342591d485"),
    ((3, 4, 6), 56, "flips-346-56-mod2.exp", "1668938ac4055ed9e2517cfa0590dffa3bc57ca04fff767e392a0d0167881f56"),
    ((2, 6, 6), 56, "flips-266-56-mod2.exp", "434c1bd4fa201f18626878e460a5deb9320475b44fd971324503c9ebe6aa77ba"),
    ((3, 5, 6), 71, "flips-356-71-mod2.exp", "7281fc6f87984855a5a38a475415c97936f272546e5d0a8b5bb1578800fb48a7"),
    ((4, 4, 6), 74, "flips-446-74-mod2.exp", "e1ad6bc2c14dad87c5d874627c33a2f35ecd061943cdf7ff3ecb207ff46cd007"),
    ((3, 6, 6), 85, "flips-366-85-mod2.exp", "555e7f429d4bfc758c4af51aa1212ffaccbc916183a4870fe2e34ffc47f79306"),
    ((4, 5, 6), 93, "flips-456-93-mod2.exp", "319a12c1eb207155d215957e7d4b3549bccbe2919ba8c7a46cb7dfdfd925f13d"),
    ((4, 6, 6), 116, "flips-466-116-mod2.exp", "fbf93ed64cb249f99b61156463adb999b80162e78bb94569e0e0425cca8b0b91"),
    ((5, 5, 6), 116, "flips-556-116-mod2.exp", "2e094d78ece74ed0a87207672af0c74539054d3c46bc3a2cccd99d76f0657259"),
    ((5, 6, 6), 144, "flips-566-144-mod2.exp", "8274d76b37fd88541c9153300a0409631ee3216971cbb29a99357baca05a7a15"),
    ((6, 6, 6), 164, "flips-666-164-mod2.exp", "6119705c25399293bff316bb1a8ed61057eb41f900c73a621625595b6c8d7706"),
)
HK_FORMAT = (6, 2, 6)          # p x 2 by 2 x n with p = 6, n = 6
LIMIT = 200

OUTPUTS = ("printed_266_terms", "printed_266_wrong", "printed_346_terms", "printed_346_wrong", "released",
           "released_exact", "released_over_rank", "released_wrong", "hopcroft_kerr_626", "probe_wrong",
           "probe_digest", "wide_coefficients", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the e-print's TeX

def tex_of(data):
    """main.tex from the source archive, read in memory (never extracted to disk)."""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        member = tf.getmember("main.tex")
        if not member.isfile():
            raise Refused("main.tex is not a file in the archive")
        return tf.extractfile(member).read().decode("utf-8")


PMATRIX = re.compile(r"\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}", re.S)
CELL = re.compile(r"\\bar\s*\{?\s*(\d+)\s*\}?|(\d+)")
BETWEEN_TERMS = re.compile(r"(\\\\)?\s*(&&|&)?\s*\+\s*(&&|&)?")


def matrix_of(body):
    rows = []
    for row in re.split(r"\\\\", body):
        if not row.strip():
            continue
        cells = []
        for cell in row.split("&"):
            c = cell.strip()
            m = CELL.fullmatch(c)
            if not m:
                raise ValueError(f"not an entry: {c!r}")
            cells.append(-int(m.group(1)) if m.group(1) is not None else int(m.group(2)))
        rows.append(cells)
    return rows


def printed_block(tex, fmt):
    head = "Here is one of our schemes of rank 56 for the format $(%d,%d,%d)$" % fmt
    if tex.count(head) != 1:
        raise Refused(f"the appendix's heading for {fmt} is not found once")
    i = tex.find(head)
    b = tex.find("\\begin{alignat*}", i)
    e = tex.find("\\end{alignat*}", b)
    if b < 0 or e < 0:
        raise Refused(f"no alignat* block after the heading for {fmt}")
    return tex[b:e]


def read_printed(block, n, m, p):
    """The terms of a printed scheme, as mm/check.py's (u, v, w) triples."""
    body = re.sub(r"^\\begin\{alignat\*\}\d*", "", block)
    mats = list(PMATRIX.finditer(body))
    if not mats or len(mats) % 3:
        raise Refused(f"{len(mats)} matrices, not a whole number of terms")
    lead = body[:mats[0].start()].strip()
    if lead not in ("", "&"):
        raise Refused(f"unexpected text before the first term: {lead!r}")
    if body[mats[-1].end():].strip():
        raise Refused("unexpected text after the last term")
    shapes = ((n, m), (m, p), (p, n))
    scheme = []
    for t in range(0, len(mats), 3):
        trip = []
        for q in range(3):
            if t + q > 0:
                sep = re.sub(r"\s+", " ", body[mats[t + q - 1].end():mats[t + q].start()]).strip()
                if q > 0 and sep != "\\otimes":
                    raise Refused(f"term {t // 3 + 1}: {sep!r} between its factors")
                if q == 0 and not BETWEEN_TERMS.fullmatch(sep):
                    raise Refused(f"term {t // 3 + 1}: {sep!r} before it")
            M = matrix_of(mats[t + q].group(1))
            rows, cols = shapes[q]
            if len(M) != rows or any(len(r) != cols for r in M):
                raise Refused(f"term {t // 3 + 1}, factor {q + 1}: not {rows} x {cols}")
            trip.append(M)
        A, B, C = trip
        u = {i * m + j: A[i][j] for i in range(n) for j in range(m) if A[i][j]}
        v = {j * p + k: B[j][k] for j in range(m) for k in range(p) if B[j][k]}
        w = {k * n + i: C[k][i] for k in range(p) for i in range(n) if C[k][i]}
        scheme.append((u, v, w))
    return scheme


# the notation of the Section 2 examples: "(a_{1,1} + a_{2,2}) \otimes (b_{1,1}) \otimes (c_{1,2}-c_{2,2})"
SYMBOL = re.compile(r"([+-]?)\s*([abc])_\{(\d+),(\d+)\}")


def symbolic_form(src, letter, rows, cols, swap=False):
    body = src.strip()
    if body.startswith("(") and body.endswith(")"):
        body = body[1:-1]
    out, rest = {}, SYMBOL.sub("", body)
    if rest.strip():
        raise ValueError(f"cannot read {src!r}")
    for sign, var, i, j in SYMBOL.findall(body):
        if var != letter:
            raise ValueError(f"{var} in a {letter}-factor: {src!r}")
        r, c = int(i) - 1, int(j) - 1
        if swap:
            r, c = c, r
        if not (0 <= r < rows and 0 <= c < cols):
            raise ValueError(f"index out of range in {src!r}")
        out[r * cols + c] = out.get(r * cols + c, 0) + (-1 if sign == "-" else 1)
    return {k: x for k, x in out.items() if x}


def section2_examples(tex, swap_c=False):
    i = tex.find("\\section{Matrix Multiplication}")
    j = tex.find("\\section{Results}", i)
    blocks = re.findall(r"\\begin\{alignat\*\}1(.*?)\\end\{alignat\*\}", tex[i:j], re.S)
    if len(blocks) != 2:
        raise Refused(f"{len(blocks)} example blocks in Section 2, not 2")
    out = []
    for blk in blocks:
        scheme = []
        for line in re.split(r"\\\\", blk):
            s = line.strip().lstrip("&").strip()
            if s.startswith("+"):
                s = s[1:]
            s = s.rstrip(",.").strip()
            if not s:
                continue
            parts = [x.strip() for x in s.split("\\otimes")]
            if len(parts) != 3:
                raise Refused(f"not a term of three factors: {s!r}")
            u = symbolic_form(parts[0], "a", 2, 2)
            v = symbolic_form(parts[1], "b", 2, 2)
            w = symbolic_form(parts[2], "c", 2, 2, swap=swap_c)
            scheme.append((u, v, w))
        out.append(scheme)
    return out


# ---------------------------------------------------------------- the checks

def hopcroft_kerr(p, n):
    """ceil((3pn + max(n, p)) / 2), in integers."""
    return (3 * p * n + max(n, p) + 1) // 2


def control(scheme, n, m, p, ring, stream):
    """mm/check.py's control, with the count a correct checker must find: one coefficient of one u_r, both drawn
    from the stream (r first, then the index), increased by one; the altered scheme is then wrong in exactly the
    entries (a, b, c) with v_r[b] w_r[c] nonzero in the ring."""
    r = stream.below(len(scheme))
    a = stream.below(n * m)
    u, v, w = scheme[r]
    u2 = dict(u)
    u2[a] = u2.get(a, 0) + 1
    altered = scheme[:r] + [(u2, v, w)] + scheme[r + 1:]
    got = check.wrong_entries(altered, n, m, p, ring)
    want = sum(1 for b, y in v.items() for c, z in w.items() if not check.is_zero(y * z, ring))
    return got, want


def wide(scheme):
    return sum(1 for t in scheme if any(abs(x) > 1 for f in t for x in f.values()))


def run(seed, results="results", log=sys.stderr):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    os.makedirs(results, exist_ok=True)
    ctl, detail_ctl = {}, {}

    # controls on the checker and the paper's own notation
    st, st_ok = check.run_selftest(seed)
    ctl["mm/check.py's self-test"] = bool(st_ok)
    detail_ctl["selftest"] = st
    tex = tex_of(check.input_bytes(*SOURCE))
    std, strassen = section2_examples(tex)
    _, strassen_swapped = section2_examples(tex, swap_c=True)
    e_std = check.wrong_entries(std, 2, 2, 2, "Z")
    e_str = check.wrong_entries(strassen, 2, 2, 2, "Z")
    e_swp = check.wrong_entries(strassen_swapped, 2, 2, 2, "Z")
    ctl["the standard algorithm of Section 2 exact (8 terms)"] = len(std) == 8 and e_std == 0
    ctl["Strassen's algorithm of Section 2 exact (7 terms)"] = len(strassen) == 7 and e_str == 0
    ctl["Strassen's with c read transposed is not"] = e_swp > 0
    detail_ctl["section2"] = {"standard_terms": len(std), "standard_wrong": e_std, "strassen_terms": len(strassen),
                              "strassen_wrong": e_str, "strassen_transposed_wrong": e_swp}

    values, detail, lines, probe_wrong = {}, {"printed": {}, "released": {}}, [], 0
    cond = {}
    for (n, m, p), rank in PRINTED:
        key = f"{n}{m}{p}"
        scheme = read_printed(printed_block(tex, (n, m, p)), n, m, p)
        terms, wrong, pw, _, ls = check.assess(f"printed_{key}", scheme, n, m, p, "Z", seed)
        got, want = control(scheme, n, m, p, "Z", check.Stream(seed, f"printed_{key}/control"))
        ctl[f"a broken copy of the printed ({n},{m},{p}) caught"] = got == want and got > 0
        values[f"printed_{key}_terms"] = terms
        values[f"printed_{key}_wrong"] = wrong
        probe_wrong += pw
        lines += ls
        detail["printed"][key] = {"terms": terms, "wrong": wrong, "probe_wrong": pw, "control": [got, want],
                                  "wide_terms": wide(scheme)}
        cond[f"the printed ({n},{m},{p}) scheme: {rank} terms, exact over the integers"] = terms == rank and wrong == 0
        print(f"printed ({n},{m},{p}): {terms} terms, {wrong} wrong", file=log)

    exact = over = total_wrong = 0
    parts = []
    for (n, m, p), rank, name, sha in RELEASED:
        data = check.input_bytes(name, sha)
        scheme = check.read_flips(data, n, m, p)
        nonempty = sum(1 for line in data.decode("ascii").splitlines() if line.strip())
        if nonempty != len(scheme):
            raise Refused(f"{name}: {nonempty} non-empty lines, {len(scheme)} products read")
        products, wrong, pw, _, ls = check.assess(f"released_{n}{m}{p}", scheme, n, m, p, "F2", seed)
        got, want = control(scheme, n, m, p, "F2", check.Stream(seed, f"released_{n}{m}{p}/control"))
        ctl[f"a broken copy of the released ({n},{m},{p}) caught"] = got == want and got > 0
        name_rank = int(name.split("-")[2])
        exact += wrong == 0
        over += products > rank
        total_wrong += wrong
        probe_wrong += pw
        lines += ls
        parts.append(f"{n}{m}{p}:{products}/{rank}")
        detail["released"][f"{n}{m}{p}"] = {"file": name, "products": products, "table_rank": rank,
                                            "name_rank": name_rank, "wrong_mod2": wrong, "probe_wrong": pw,
                                            "control": [got, want]}
        print(f"released ({n},{m},{p}): {products} products (table {rank}), {wrong} wrong mod 2", file=log)
    cond["every released file exact modulo 2, within its table rank"] = exact == len(RELEASED) and over == 0
    hk = hopcroft_kerr(HK_FORMAT[0], HK_FORMAT[2])
    cond["Hopcroft and Kerr's count for (6,2,6) above 56"] = hk > 56

    values.update({
        "released": "products/table rank: " + ", ".join(parts),
        "released_exact": exact,
        "released_over_rank": over,
        "released_wrong": total_wrong,
        "hopcroft_kerr_626": hk,
        "probe_wrong": probe_wrong,
        "probe_digest": check.digest(lines),
        "wide_coefficients": ", ".join(f"({k[0]},{k[1]},{k[2]}) {v['wide_terms']} of {v['terms']} terms"
                                       for k, v in detail["printed"].items()),
        "conditions_met": sum(cond.values()),
        "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()),
        "controls_total": len(ctl),
    })
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail.update({"conditions": cond, "controls": ctl, "control_statistics": detail_ctl, "test": TEST})
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"km2023: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
