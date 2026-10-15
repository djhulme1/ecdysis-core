#!/usr/bin/env python3
"""Kauers & Wood's meta flip graph: one released scheme for each of the 28 formats whose rank bound the paper improves,
checked exactly over the ring it states, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from M. Kauers and I. Wood, "Exploring the Meta
Flip Graph for Matrix Multiplication" (arXiv:2510.19787v1, October 2025): "Continuing recent investigations of bounding
the tensor rank of matrix multiplication using flip graphs, we present here improved rank bounds for about thirty matrix
formats."

The test, as registered: see TEST below. Standard library only, in the python image, no network. The inputs are the
claim's data of record, each checked against its SHA-256 before anything else runs and read as text: the e-print's
source (arXiv-2510.19787v1.tar.gz: main.tex and table.tex) and, for each format of the paper's table, one scheme the
authors released (mkauers/matrix-multiplication at 6487519, the paper's day, GPL-3.0), chosen before registering by
the rule of 2. Nothing in them is run. Every rule below was fixed before any scheme's exactness was computed.

1. The table. table.tex is read row by row (a % line is a comment): the format as three digits (n, m, p), its old rank
   \\o{r}, and the cells; the \\b{r} cells are the lowest rank found for it ("highlighted in bold face"), and must
   agree within a row. 28 rows. The rings, from main.tex, each sentence found exactly once: Z_2 for the formats of "For
   the formats $(4,5,6)$, $(3,7,8)$ and $(3,8,8)$, the improvement appears to work only over~$\\set Z_2$."; Q for those
   of "The other exceptional formats are ... where Hensel lifting did not lead to integer coefficients but only to
   coefficients in~$\\set Q$."; Z for every other format ("In most of the cases, at least one scheme of smallest rank
   could be lifted to schemes with coefficients in~$\\set Z$").
2. The files (fixed when the claim was registered, named in its data of record): for each format, among the .exp files
   of its directory at 6487519 with the bold rank's number of products, in name order, the first whose coefficients
   lie in its ring as the release writes it: for Z a file with no divisor and no .mod2 in its name, for Q one with no
   .mod2, for Z_2 a .mod2.exp file.
3. Reading (mm/check.py's reader of the .exp format, with one addition): one product per line,
   (A-form)*(B-form)*(C-form) over a_ij (n x m), b_jk (m x p) and c_ki (p x n), the C-variables naming the output entry
   C_ik transposed as the format does; a line -( ... ) is a negated product; a product followed by /d (d a positive
   integer) is divided by d, which only a Q scheme may do. Any other text refuses the run.
4. Exactness (mm/check.py's Brent equations): every one of the (nm)(mp)(pn) coefficients of the sum of the products
   equals that of the tensor of <n, m, p>, 1 at (i*m + j, j*p + k, k*n + i) and 0 elsewhere: over Z in integers, over
   Q in exact fractions, over Z_2 modulo 2.
5. The test's 28 conditions, one per format: its file holds exactly the bold rank's number of products and is exact
   over its ring. test_passed is 1 if all 28 hold.
6. Beside the test, none of it counted: the gains over the old ranks; the integer and rational schemes also checked
   modulo 2 (their denominators are odd); the Z_2 schemes also read over the integers, which the paper says they do
   not satisfy; the primes in the rational schemes' divisors, against the paper's "for (2,5,8) ... Z[1/3,1/5,1/7]",
   "for (2,6,8) ... Z[1/3,1/5,1/11]", "for (3,4,8), we even need denominators with twelve distinct prime factors" and
   "For all other formats where we managed to obtain rational coefficients, these turn out to be in Z[1/3]"; three
   products of seed-drawn matrices through each scheme against the schoolbook product (mm/check.py's probe), and their
   digest; the largest coefficient and the nonzeros.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): Strassen's 2 x 2 scheme exact
in 7 products; the naive scheme of (2,5,7) exact in 70 products, and wrong once a product is dropped; and in each
released scheme one coefficient of a seed-chosen product raised by one (mm/check.py's control) makes exactly
|v_r| |w_r| coefficients wrong, over its ring.

What it cannot check: the old ranks, which the paper takes from Sedoglavic's table; the other released schemes of each
format; the searches that found them.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 mm/mfg.py
"""

import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tarfile
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_check", os.path.join(HERE, "check.py"))
CHECK = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CHECK)

EPRINT = ("arXiv-2510.19787v1.tar.gz", "6ce83d2af8df5559cd6fa191740eabf60b14de2dbe2906e2c44ab3c833d70736")
SCHEME_LIST = [   # the data of record, fixed at registration (rule 2): (format, input name, sha256)
    ("257", "mfg-257-k108391c6c35ad0c4.exp", "a63e4a62bb1241435b83e9ac9f9d77c2bcb3320e40e78c68c4a0ff245f7d92e2"),
    ("258", "mfg-258-k302e5af94fb52fb6.exp", "18cd7839d7be9a1b7de2c8e0cb66ba347c01be5cdf296a5ff0cf7927969c5485"),
    ("267", "mfg-267-k1487a4604127952d.exp", "0368829ebcc15938909c3acf6572b689507487f7f07bf261cf23035ba13be385"),
    ("268", "mfg-268-k18947ac96dd12ceb.exp", "9be570a73fad4745fe3633fe1f621b16b11fa7b7829266549462b68a4e6c2f43"),
    ("277", "mfg-277-k128251be9bc28ac9.exp", "a9aeb707b170965e149ae8f2bc1d97572e2c245bd00ecb857fc8b231afc25abe"),
    ("346", "mfg-346-k121761c9fceb6f0b.exp", "490c1086a162388127a654a5511d8d977df91d609a1e741c58e801c1077ca466"),
    ("347", "mfg-347-k19a00ff7f82ef49.exp", "b9e50ef1be90bada4b2efcc22299e4dd651795d93def1239aaf7619ae6b426dc"),
    ("348", "mfg-348-k405c7a16be176729.exp", "a5b491043c76ec69ee480d40a1b105ceeaff205d460d464b04f1bbf843967221"),
    ("357", "mfg-357-k168c50bec35cf94e.exp", "cc08501f17bd40afddf65a702c57317cf696728e9423818b119271d54c18c2cb"),
    ("358", "mfg-358-k37e78eeab4e20915.exp", "a63b8b004b6093827e58acce38e0ecadda22ddd55c2e63ffc2d3c758f5fd2831"),
    ("368", "mfg-368-01bcef89f1.exp", "96d92796bce3eec40bbdf644d28b16d41eb4d85abd719da8982ccd3b4cb200a0"),
    ("377", "mfg-377-k1163af2837b2070.exp", "7579186de4425471c3068b128d6347cbebc494caea930228e2a944b6774e9090"),
    ("378", "mfg-378-ffdb2d875f.mod2.exp", "44aa1a12c2cfc49d0fd59b7a1a770b9ba253adc651eb8b7ef2925dd94620bda2"),
    ("388", "mfg-388-ff888d88d5.mod2.exp", "aedb42405c40ab283ff5a6de1badd6b1217c37aec8cccca4713dedd4d006dfb5"),
    ("446", "mfg-446-k0ac013b97cb3ae5.exp", "0a0a8c72f4443fad17fba10c19856226564b683789fcd713a6663c001db7853c"),
    ("456", "mfg-456-k08dcabe7aa6634b.mod2.exp", "848598e02b5b4972b6e3aad7f30340fdadd9e9776d4f5250c42615e4e2ddfbc5"),
    ("457", "mfg-457-k023c869f4a9c2e4.exp", "27db9a5045ea6944c1e3de6f780cd81f1c97bf23fcefd3de779c518da47d1db0"),
    ("458", "mfg-458-k10f2d8a1de6a5616.exp", "fc5dc788b9f73d0d9d18b378ee5a8757d5c629da23eef84d5ea8336bffd6d323"),
    ("467", "mfg-467-k049c136198369dc.exp", "595838b66ea8b565e5ce5e879bfb628025dc81b46d4765deef5c18aee2a38370"),
    ("477", "mfg-477-k335db443c7f886d3.exp", "646de63e449903d65c53b468f96fbcc3e4c5a5699ed6ccde21c5ad816e06e7b0"),
    ("556", "mfg-556-k0005554e963ccfc.exp", "0a9e393d3796e82b592c934c8c90ad9d3ca6a271dda0ed0ab9f52a317b5b6e4f"),
    ("557", "mfg-557-k03b411c9170e106.exp", "a368e7219d6fd2a9c2553910b338fd3b5b69b7067884fd405e1c4f849760301d"),
    ("558", "mfg-558-k33e3e3af75a56568.exp", "bfb4afb15a824abf556791ac74c1399403a2cebdbc54c3acafad5d3f6caa3438"),
    ("566", "mfg-566-k00a896503266bf0.exp", "fa04b7093ff5333126f4fdc835834a4b2a8b2619441dc9e9e49159c7f87a72e1"),
    ("567", "mfg-567-k12ca7d002f487a1d.exp", "6fcc19b06edd534de6e5c4214d542de5bba37fc50be27f143748d3f18803b1c8"),
    ("568", "mfg-568-k1844566e012fe5f1.exp", "1781d9e732ef61379fe4a5d24903cff85f2cef91400116d24081a0186ca5c173"),
    ("577", "mfg-577-k1af12101f45552ca.exp", "72177982388b8ab087dc3ddcf2bcab4323bb5151652f93a3de0f791428d38722"),
    ("667", "mfg-667-k1b9c131fc81094d0.exp", "a52ee4bb453eaf6f3ebf86e7b49fecfbf9f53de10055c2cc476b6fb6e7b0427a"),
]
Z2_SENTENCE = ("For the formats $(4,5,6)$, $(3,7,8)$ and $(3,8,8)$, the improvement appears to work only over~$\\set "
               "Z_2$.")
Q_START = "The other exceptional formats are"
Q_END = "where Hensel lifting did not lead to integer coefficients but only to coefficients in~$\\set Q$."
DENOMINATORS = {"258": {3, 5, 7}, "268": {3, 5, 11}}
TWELVE = "348"
PROBES = 3
LIMIT = 200
RINGS = {"Z": "Z", "Q": "Q", "Z2": "F2"}

TEST = ("Refuted if, for any of the 28 formats in the e-print's table, its scheme in the data of record (the authors' "
        "release at mkauers/matrix-multiplication 6487519, one file per format with the table's bold rank of "
        "products) is not an exact decomposition of the matrix multiplication tensor in that many products over the "
        "ring the paper states for it: Z_2 for (4,5,6), (3,7,8) and (3,8,8); Q for (2,5,7), (2,5,8), (3,4,8), "
        "(3,5,7), (2,6,8), (2,7,7) and (3,7,7); Z for the other 18.")

OUTPUTS = ("table", "rings", "exact", "inexact", "ranks_a", "ranks_b", "gains", "mod2_of_others", "z2_over_integers",
           "denominators", "probes", "probe_digest", "altered", "coefficients", "conditions_met", "conditions_total",
           "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- inputs and the paper (rules 1 and 2)

def read_input(inputs, name, sha):
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != sha:
        raise Refused(f"{name}: not the data of record")
    return data


def eprint_files(data):
    try:
        tar = tarfile.open(fileobj=io.BytesIO(gzip.decompress(data)))
    except (OSError, tarfile.TarError) as e:
        raise Refused(f"the e-print does not unpack: {e}")
    out = {}
    for m in tar.getmembers():
        if m.isfile() and m.name in ("main.tex", "table.tex"):
            out[m.name] = tar.extractfile(m).read().decode("ascii")
    if set(out) != {"main.tex", "table.tex"}:
        raise Refused("the e-print lacks main.tex or table.tex")
    return out


def fmt_of(code):
    if not re.fullmatch(r"[2-9]{3}", code):
        raise Refused(f"not a format: {code!r}")
    return tuple(int(c) for c in code)


def read_table(text):
    rows = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        cells = [c.strip() for c in s.rstrip("\\").split("&")]
        old = re.fullmatch(r"\\o\{(\d+)\}", cells[1] if len(cells) > 1 else "")
        if not old:
            raise Refused(f"a row without an old rank: {s[:60]!r}")
        bold = [int(x) for c in cells[2:] for x in re.findall(r"\\b\{(\d+)\}", c)]
        if not bold or len(set(bold)) != 1:
            raise Refused(f"a row whose bold ranks are missing or differ: {s[:60]!r}")
        fmt_of(cells[0])
        if cells[0] in rows:
            raise Refused(f"format {cells[0]} twice")
        rows[cells[0]] = {"old": int(old.group(1)), "best": bold[0]}
    if len(rows) != 28:
        raise Refused(f"{len(rows)} rows, not 28")
    return rows


def formats_in(sentence):
    return ["".join(t) for t in re.findall(r"\$\((\d),(\d),(\d)\)\$", sentence)]


def read_rings(main, rows):
    text = " ".join(main.split())
    if text.count(Z2_SENTENCE) != 1:
        raise Refused("the Z_2 sentence is not found exactly once")
    i = text.find(Q_START)
    j = text.find(Q_END, i)
    if i < 0 or j < 0 or text.count(Q_START) != 1 or text.count(Q_END) != 1:
        raise Refused("the Q sentence is not found exactly once")
    z2, q = formats_in(Z2_SENTENCE), formats_in(text[i:j])
    if len(z2) != 3 or len(q) != 7 or set(z2) & set(q) or not (set(z2) | set(q)) <= set(rows):
        raise Refused(f"the rings do not read as stated: {z2} {q}")
    return {f: ("Z2" if f in z2 else "Q" if f in q else "Z") for f in rows}


# ---------------------------------------------------------------- reading a scheme (rule 3)

TAIL = re.compile(r"^(.*\))\s*/\s*(\d+)$")


def read_scheme(data, fmt, ring):
    n, m, p = fmt
    scheme, divisors = [], []
    for line in data.decode("ascii").splitlines():
        s = line.strip()
        if not s:
            continue
        div = 1
        t = TAIL.match(s)
        if t:
            s, div = t.group(1).strip(), int(t.group(2))
            if div <= 0:
                raise Refused(f"a zero divisor: {line[:60]!r}")
            if ring != "Q":
                raise Refused(f"a divisor in a {ring} scheme: {line[:60]!r}")
        sign = 1
        if s.startswith("-(") and CHECK.closing(s, 1) == len(s) - 1:
            s, sign = s[2:-1], -1
        parts = CHECK.split_product(s)
        if len(parts) != 3:
            raise Refused(f"not a product of three factors: {line[:60]!r}")
        try:
            u = CHECK.linear_form(parts[0], "a", n, m)
            v = CHECK.linear_form(parts[1], "b", m, p)
            w = CHECK.linear_form(parts[2], "c", p, n)
        except ValueError as e:
            raise Refused(str(e))
        if ring == "Q":
            scale = Fraction(sign, div)
            u = {k: Fraction(x) * scale for k, x in u.items()}
        else:
            u = {k: sign * x for k, x in u.items()}
        if ring == "Z2":
            u, v, w = ({k: x % 2 for k, x in f.items() if x % 2} for f in (u, v, w))
        divisors.append(div)
        scheme.append(tuple(CHECK.columns([u, v, w])))
    return scheme, divisors


def as_integers(data, fmt):
    """A .mod2 file read over the integers, for the beside check."""
    return read_scheme(data, fmt, "Z")[0]


def primes_of(d):
    out, q = set(), 2
    while q * q <= d:
        while d % q == 0:
            out.add(q)
            d //= q
        q += 1
    if d > 1:
        out.add(d)
    return out


def naive(n, m, p):
    return [({i * m + j: 1}, {j * p + k: 1}, {k * n + i: 1}) for i in range(n) for j in range(m) for k in range(p)]


# ---------------------------------------------------------------- run

def run(seed, inputs="inputs", results="results", log=sys.stderr):
    if not re.fullmatch(r"[0-9a-f]{64}", seed or ""):
        raise Refused("the seed must be 64 hex characters")
    if len(SCHEME_LIST) != 28:
        raise Refused("the data of record is not named")
    paper = eprint_files(read_input(inputs, *EPRINT))
    rows = read_table(paper["table.tex"])
    rings = read_rings(paper["main.tex"], rows)
    if {f for f, _, _ in SCHEME_LIST} != set(rows):
        raise Refused("the data of record does not name one file per format of the table")

    found, cond, probe_lines = {}, {}, []
    for code, name, sha in SCHEME_LIST:
        fmt, ring = fmt_of(code), rings[code]
        data = read_input(inputs, name, sha)
        scheme, divisors = read_scheme(data, fmt, ring)
        n, m, p = fmt
        r = RINGS[ring]
        products, wrong, probe_wrong, control_wrong, lines = CHECK.assess(f"mfg/{code}", scheme, n, m, p, r, seed,
                                                                          PROBES)
        probe_lines.extend(lines)
        expected_control = expected_altered(scheme, n, m, f"mfg/{code}", seed)
        f = {"ring": ring, "products": products, "best": rows[code]["best"], "old": rows[code]["old"], "wrong": wrong,
             "probe_wrong": probe_wrong, "control_wrong": control_wrong, "control_expected": expected_control,
             "max_coefficient": str(max(abs(x) for t in scheme for d in t for x in d.values())),
             "nonzeros": sum(len(d) for t in scheme for d in t)}
        if ring in ("Z", "Q"):
            f["wrong_mod2"] = CHECK.wrong_entries(mod2_of(scheme), n, m, p, "F2")
        else:
            f["wrong_over_integers"] = CHECK.wrong_entries(as_integers(data, fmt), n, m, p, "Z")
        if ring == "Q":
            f["primes"] = sorted(set().union(*(primes_of(d) for d in divisors)))
        found[code] = f
        cond[f"({n},{m},{p}) in {rows[code]['best']} over {ring}: exact"] = (products == rows[code]["best"] and
                                                                              wrong == 0)
        print(f"({n},{m},{p}) {ring}: {products} products, wrong {wrong}, probes {probe_wrong}", file=log)

    ctl = {}
    s = CHECK.strassen()
    ctl["Strassen's 2 x 2 scheme exact in 7 products"] = len(s) == 7 and CHECK.wrong_entries(s, 2, 2, 2, "Z") == 0
    nv = naive(2, 5, 7)
    ctl["the naive (2,5,7) scheme exact in 70, wrong with a product dropped"] = (
        len(nv) == 70 and CHECK.wrong_entries(nv, 2, 5, 7, "Z") == 0 and CHECK.wrong_entries(nv[1:], 2, 5, 7, "Z") > 0)
    ctl["each scheme: a raised coefficient makes |v_r| |w_r| entries wrong"] = all(
        f["control_wrong"] == f["control_expected"] and f["control_wrong"] > 0 for f in found.values())
    print(f"controls: {sum(ctl.values())} of {len(ctl)}", file=log)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")

    order = sorted(found, key=lambda c: (rows[c]["best"], c))
    half = len(order) // 2

    def listing(codes):
        return ", ".join(f"{c} {found[c]['products']}" for c in codes)
    gains = {c: rows[c]["old"] - rows[c]["best"] for c in rows}
    others = [c for c in found if found[c]["ring"] in ("Z", "Q")]
    z2 = [c for c in found if found[c]["ring"] == "Z2"]
    qs = sorted(c for c in found if found[c]["ring"] == "Q")
    paper_primes_ok = {c: (set(found[c]["primes"]) == DENOMINATORS[c] if c in DENOMINATORS else
                           len(found[c]["primes"]) == 12 if c == TWELVE else
                           set(found[c]["primes"]) in ({3}, {5})) for c in qs}
    top = max(found, key=lambda c: Fraction(found[c]["max_coefficient"]))
    values = {
        "table": f"{len(rows)} formats; bold ranks below the old by {min(gains.values())} to {max(gains.values())}",
        "rings": "over Z " + str(sum(1 for c in rings if rings[c] == "Z")) + ", Q " + str(len(qs)) + ", Z_2 "
                 + str(len(z2)),
        "exact": sum(1 for c in found if found[c]["wrong"] == 0 and found[c]["products"] == rows[c]["best"]),
        "inexact": ", ".join(c for c in sorted(found) if not cond[f"({c[0]},{c[1]},{c[2]}) in {rows[c]['best']} over "
                                                                f"{rings[c]}: exact"]) or "none",
        "ranks_a": listing(order[:half]),
        "ranks_b": listing(order[half:]),
        "gains": f"over the old ranks: {sum(gains.values())} products in all; largest {max(gains.values())} "
                 f"({', '.join(c for c in sorted(gains) if gains[c] == max(gains.values()))})",
        "mod2_of_others": f"{sum(1 for c in others if found[c]['wrong_mod2'] == 0)} of the {len(others)} Z and Q "
                          f"schemes also exact modulo 2",
        "z2_over_integers": "wrong entries over the integers: " + ", ".join(
            f"{c} {found[c]['wrong_over_integers']}" for c in sorted(z2)),
        "denominators": "; ".join(f"{c} {','.join(str(q) for q in found[c]['primes'])}" for c in qs
                                  if c != TWELVE) + f"; {TWELVE}: {len(found[TWELVE]['primes'])} primes; as the paper "
                                                    f"says: {sum(paper_primes_ok.values())} of {len(qs)}",
        "probes": sum(f["probe_wrong"] for f in found.values()),
        "probe_digest": CHECK.digest(probe_lines),
        "altered": f"{sum(1 for f in found.values() if f['control_wrong'] == f['control_expected'])} of 28 as |v||w|",
        "coefficients": (f"largest |coefficient| {found[top]['max_coefficient']} ({top}); nonzeros "
                         f"{min(f['nonzeros'] for f in found.values())} to {max(f['nonzeros'] for f in found.values())}"),
        "conditions_met": sum(cond.values()),
        "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()),
        "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"conditions": cond, "controls": ctl, "rows": rows, "rings": rings, "found": found,
              "paper_primes": paper_primes_ok, "test": TEST}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return out, detail


def mod2_of(scheme):
    """A Z or Q scheme reduced modulo 2: each coefficient's odd denominator inverted (it is 1 modulo 2)."""
    out = []
    for t in scheme:
        g = []
        for d in t:
            h = {}
            for k, x in d.items():
                x = Fraction(x)
                if x.denominator % 2 == 0:
                    raise Refused("an even denominator has no image modulo 2")
                if x.numerator % 2:
                    h[k] = 1
            g.append(h)
        out.append(tuple(g))
    return out


def expected_altered(scheme, n, m, name, seed):
    """|v_r| |w_r| for the product mm/check.py's control raises, drawn from the same stream."""
    st = CHECK.Stream(seed, f"{name}/control")
    r = st.below(len(scheme))
    st.below(n * m)
    _, v, w = scheme[r]
    return len(v) * len(w)


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"mfg: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
