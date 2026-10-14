#!/usr/bin/env python3
"""Kauers & Wood's consequences of the Moosbauer-Poole algorithms: eight of their released schemes checked exactly, for
an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:155269075bc78837) is from Kauers & Wood,
"Consequences of the Moosbauer-Poole Algorithms" (arXiv:2505.05896v1, May 2025): "Taking these multiplication schemes as
starting points, we found improved matrix multiplication schemes for various rectangular matrix formats using a flip
graph search."

Its registered test: refuted if, for any of the eight formats with the largest gains in the paper's table ((4,5,6) 90,
(4,5,7) 104, (5,5,6) 110, (5,5,7) 127, (5,6,6) 130, (4,7,7) 144, (5,6,7) 150, (5,7,7) 176, against previous records 93,
109, 116, 133, 137, 147, 159, 185), the scheme the authors released for it (mkauers/matrix-multiplication at 00d5ab3,
the commit of the paper's v1; the data of record) is not an exact decomposition of the matrix multiplication tensor over
the integers in that many products.

The inputs are the eight .exp files of the data of record, each checked against its SHA-256 and read as text with
mm/check.py's reader of the .exp format; nothing in them is run. Every rule below was fixed before any of the files'
exactness was computed.

1. Reading. One product per line, (A-form)*(B-form)*(C-form), over a_ij (n x m), b_jk (m x p) and c_ki (p x n), the
   format's (n, m, p) being the directory the file was released in; a line -( ... ) is a negated product. The reader
   refuses any variable outside those ranges.
2. Exactness (mm/check.py's Brent equations): every one of the (nm)(mp)(pn) coefficients of the sum of the products
   equals that of the tensor of <n, m, p>, 1 at (i*m + j, j*p + k, k*n + i) and 0 elsewhere, over the integers.
3. The test's eight conditions, one per format: the file holds exactly the printed number of products and is exact over
   the integers. test_passed is 1 if all eight hold.
4. Beside the test: exactness modulo 2; three products of seed-drawn integer matrices (entries -9 to 9) through each
   scheme against the schoolbook product, and their digest; the largest coefficient and the number of nonzero
   coefficients; the gains over the table's previous records and over the naive rank nmp.
5. Controls: Strassen's 2 x 2 scheme exact in 7 products; the naive scheme of (4,5,6) exact in 120 products and one
   coefficient wrong once a product is dropped; and, in each released scheme, one coefficient of a seed-chosen product
   raised by one (mm/check.py's control) makes exactly |v_r| |w_r| coefficients wrong.

What it cannot check: the two other improved formats ((4,6,7) 123 and (6,6,7) 183, left out as the archive takes eight
files), the other released schemes of each format, and the previous records, which the paper takes from Sedoglavic's
table of April 2025.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 mm/kw.py
"""

import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_check", os.path.join(HERE, "check.py"))
CHECK = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CHECK)

INPUTS = {
    (4, 5, 6): ("kw-456-k0e7ba384e845ae2.exp", "648c223da83c2534da343a707e6f30112e99be9f34c65ac765415d322a6c48b5"),
    (4, 5, 7): ("kw-457-k0648be174ad1e03.exp", "cd05f91a3a17883dd27d7c726d4418d146f7572df2217d825f28ca59af014869"),
    (4, 7, 7): ("kw-477-k335db443c7f886d3.exp", "646de63e449903d65c53b468f96fbcc3e4c5a5699ed6ccde21c5ad816e06e7b0"),
    (5, 5, 6): ("kw-556-k03ff46ef9048539.exp", "6893ab9622d864b718763b2eed39e738a8b0a1b1f5f17113b3664505ee5a89da"),
    (5, 5, 7): ("kw-557-k100932c5b32208dd.exp", "d1fa7861abacb9cd5b8daf5952957a4dc66c6361831614f78efcb093740f5d35"),
    (5, 6, 6): ("kw-566-k10c786b9109095c4.exp", "7d47cc04230472eb075b7cc86624e24d58eec2c6abebf6bd7bb21badd1ba46fd"),
    (5, 6, 7): ("kw-567-k12ca7d002f487a1d.exp", "6fcc19b06edd534de6e5c4214d542de5bba37fc50be27f143748d3f18803b1c8"),
    (5, 7, 7): ("kw-577-k1af12101f45552ca.exp", "72177982388b8ab087dc3ddcf2bcab4323bb5151652f93a3de0f791428d38722"),
}
# The paper's table, for these formats: naive rank, previous record, its rank; in the table's order.
TABLE = {(4, 5, 6): (120, 93, 90), (4, 5, 7): (140, 109, 104), (5, 5, 6): (150, 116, 110), (5, 5, 7): (175, 133, 127),
         (5, 6, 6): (180, 137, 130), (4, 7, 7): (196, 147, 144), (5, 6, 7): (210, 159, 150), (5, 7, 7): (245, 185, 176)}
ORDER = [(4, 5, 6), (4, 5, 7), (5, 5, 6), (5, 5, 7), (5, 6, 6), (4, 7, 7), (5, 6, 7), (5, 7, 7)]
PROBES = 3
OUTPUTS = ("schemes", "exact_integers", "exact_mod_2", "probes", "probe_digest", "altered", "coefficients", "gains",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


def read_input(inputs, fmt):
    name, sha = INPUTS[fmt]
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha:
        raise Refused(f"{name}: sha256 {got}, not the registered {sha}")
    return data


def fmt_name(fmt):
    return "(" + ",".join(str(x) for x in fmt) + ")"


def naive(n, m, p):
    """The schoolbook scheme of <n, m, p>: one product a_ij b_jk per (i, j, k), into c_ki."""
    return [({i * m + j: 1}, {j * p + k: 1}, {k * n + i: 1}) for i in range(n) for j in range(m) for k in range(p)]


def expected_altered(scheme, name, seed):
    """The number of wrong coefficients mm/check.py's control must find: |v_r| |w_r| for the product r it alters."""
    r = CHECK.Stream(seed, f"{name}/control").below(len(scheme))
    _, v, w = scheme[r]
    return len(v) * len(w)


def coefficient_stats(scheme):
    vals = [abs(x) for triple in scheme for form in triple for x in form.values()]
    return max(vals), len(vals)


def conditions(found):
    return {f"{fmt_name(fmt)} exact over the integers in {TABLE[fmt][2]} products":
            found[fmt]["products"] == TABLE[fmt][2] and found[fmt]["wrong_integers"] == 0 for fmt in ORDER}


def controls_known(seed):
    s = CHECK.strassen()
    strassen_ok = len(s) == 7 and CHECK.wrong_entries(s, 2, 2, 2, "Z") == 0
    nv = naive(4, 5, 6)
    naive_ok = len(nv) == 120 and CHECK.wrong_entries(nv, 4, 5, 6, "Z") == 0 \
        and CHECK.wrong_entries(nv[1:], 4, 5, 6, "Z") == 1
    return {"Strassen's scheme is exact in 7 products": strassen_ok,
            "the naive (4,5,6) scheme is exact in 120 and one coefficient wrong without a product": naive_ok}


def listing(values):
    return ", ".join(str(v) for v in values)


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    found = {}
    lines = []
    for fmt in ORDER:
        n, m, p = fmt
        data = read_input(inputs, fmt)
        scheme = CHECK.read_flips(data, n, m, p)
        nonblank = sum(1 for line in data.decode("ascii").splitlines() if line.strip())
        name = INPUTS[fmt][0]
        products, wrong_z, probe_wrong, control_wrong, plines = CHECK.assess(name, scheme, n, m, p, "Z", seed, PROBES)
        lines += plines
        top, nonzeros = coefficient_stats(scheme)
        found[fmt] = {"products": products, "lines": nonblank, "wrong_integers": wrong_z,
                      "wrong_mod_2": CHECK.wrong_entries(scheme, n, m, p, "F2"), "probe_wrong": probe_wrong,
                      "altered_wrong": control_wrong, "altered_expected": expected_altered(scheme, name, seed),
                      "largest_coefficient": top, "nonzeros": nonzeros}
    cond = conditions(found)
    controls = controls_known(seed)
    controls["one raised coefficient makes |v_r| |w_r| coefficients wrong in every released scheme"] = all(
        f["altered_wrong"] == f["altered_expected"] and f["altered_wrong"] > 0 for f in found.values())
    values = {
        "schemes": "products by format: " + "; ".join(f"{fmt_name(f)} {found[f]['products']}" for f in ORDER),
        "exact_integers": "wrong coefficients over the integers: " + listing(found[f]["wrong_integers"] for f in ORDER),
        "exact_mod_2": "wrong coefficients modulo 2: " + listing(found[f]["wrong_mod_2"] for f in ORDER),
        "probes": f"wrong entries in {PROBES} seed-drawn integer products each: "
                  + listing(found[f]["probe_wrong"] for f in ORDER),
        "probe_digest": CHECK.digest(lines),
        "altered": "one raised coefficient: wrong " + listing(found[f]["altered_wrong"] for f in ORDER)
                   + " (|v||w|: " + listing(found[f]["altered_expected"] for f in ORDER) + ")",
        "coefficients": "largest |coefficient| " + listing(found[f]["largest_coefficient"] for f in ORDER)
                        + "; nonzeros " + listing(found[f]["nonzeros"] for f in ORDER),
        "gains": "below the previous record by " + listing(TABLE[f][1] - found[f]["products"] for f in ORDER)
                 + "; below nmp by " + listing(TABLE[f][0] - found[f]["products"] for f in ORDER),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": {fmt_name(f): {"name": n_, "sha256": s} for f, (n_, s) in INPUTS.items()},
              "conditions": cond, "controls": controls,
              "schemes": {fmt_name(f): found[f] for f in ORDER},
              "table": {fmt_name(f): {"naive": TABLE[f][0], "previous": TABLE[f][1], "paper": TABLE[f][2]} for f in ORDER},
              "probe_lines": len(lines)}
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
        sys.exit(f"kw: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
