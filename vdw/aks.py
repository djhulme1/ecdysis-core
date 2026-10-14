#!/usr/bin/env python3
"""Ahmed, Kullmann & Snevily's certificates: w(2;3,t) > t^2 for t = 24 to 30.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:de5e8c7ceb990860) is from Ahmed, Kullmann &
Snevily, "On the van der Waerden numbers w(2;3,t)" (Discrete Applied Mathematics 174, 27-51, 2014; arXiv:1102.5433):
"The lower bounds for 24 <= t <= 30 refute the conjecture that w(2;3,t) <= t^2, and we present an improved
conjecture."

Its registered test: refuted if, read from the e-print's TeX, the certificate it prints for any t from 24 to 30 (the
good partitions behind its conjectured lower bounds w(2;3,t) >= 593, 656, 727, 770, 827, 868 and 903) is not a good
partition of {1, ..., n - 1} for its bound n, a word in 0 and 1 of that length whose 0s contain no 3-term arithmetic
progression and whose 1s no t-term one; or if n - 1 < t^2, so that w(2;3,t) > t^2 is not shown.

Standard library only. The input is the claim's data of record, the e-print (arXiv-1102.5433v4.tex.gz, the gzip of the
paper's one TeX file), checked against its SHA-256 and size and read in memory; its text is read as data and nothing in
it is run. Every rule below was fixed before any seed existed.

1. Reading. In the appendix's subsection "Conjectured precise lower bounds", each paragraph headed
   "\\vdw(2; 3, t)\\geq n" (t = 20 to 30) is followed by display math holding a word; in "Further lower bounds", each
   paragraph headed "\\vdw(2; 3, t) > n" (t = 31 to 39) by a gather environment. The example good partition of
   {1, ..., 348} in Section 3.1 (w(2;3,19) >= 349) is read the same way, and so are the paper's table of known values
   (t = 3 to 19), its two tables of lower bounds and its table of good palindromic partitions (t = 3 to 39). A word is
   the paper's notation (its Section 1.2): bits 0 and 1, b^{k} meaning k copies of b; layout (dollars, line breaks,
   gather) and a final full stop are removed, anything else refuses the run.
2. A good partition of {1, ..., m} w.r.t. (3, t) (the paper's definition, in its Section 1): a word of length m whose
   0-positions P_0 contain no 3-term arithmetic progression and whose 1-positions P_1 no t-term one. A heading "\\geq n"
   asks for a good partition of {1, ..., n - 1}, "> n" for one of {1, ..., n}.
3. The test's two conditions, for every t from 24 to 30: the printed word is a good partition of {1, ..., n - 1} with n
   its heading's bound; and n - 1 >= t^2 (a good partition of {1, ..., t^2} or more shows w(2;3,t) > t^2).
   test_passed is 1 if both hold for all seven.
4. Beside the test, none of it counted: the same check for t = 20 to 23, for t = 31 to 39 and for the w(2;3,19) example
   (a good partition of {1, ..., 348}, one less than the known value); the headings against the paper's two tables of
   lower bounds; whether either one-letter extension of each word for t = 20 to 30 (a 0 or a 1 appended) is still good,
   which the conjectured exactness says it is not; every good palindromic partition of the palindromic table, expanded
   from the half the paper prints (length ceil(m/2); the word reads the same from both ends), checked good for its size;
   the paper's improved conjecture, w(2;3,t) <= 77/46 t^2, against every value it prints for t = 3 to 39 (a known value
   or a bound "\\geq n" is within it if n <= 77/46 t^2, a bound "> n" if n + 1 <= 77/46 t^2); the paper's d, the
   largest (w(2;3,t) - w(2;3,t-1))/(t - 1) over t = 4 to 39 with the printed values, which it gives as
   (593 - 516)/23 = 77/23; and, where the TeX prints them as read here, its Ansatz w_t := 9 + sum_{i=3}^{t-1} d i
   against the closed form it prints, d/2 t^2 - 3/2 d t + 9 - 2d, and against d/2 t^2, for t = 3 to 39.

Controls (controls_passed counts those that behave as stated): exhaustive enumeration gives w(2;3,3) = 9 and
w(2;3,4) = 18 (the first two entries of the paper's table of known values); a 0 planted in the t = 24 word at a
seed-drawn position completing a 3-term progression of 0s is caught; the t = 24 word shortened by one letter fails its
length; and a direct triple loop over all progressions agrees with the fast check on the t = 24 and t = 30 words.

What it cannot check: w(2;3,19) = 349 itself, whose other half (no good partition of {1, ..., 349}) took the authors
roughly 196 years of CPU time, and the exactness the paper conjectures for t = 20 to 30.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 vdw/aks.py
"""

import gzip
import hashlib
import json
import os
import re
import sys
from fractions import Fraction

EPRINT = ("arXiv-1102.5433v4.tex.gz", "21e5f1307f57c8ae471b0a53b940b01f9f56a870f82c13787b9fa9e2f9965aab", 62374)
TEST_T = range(24, 31)
LIMIT = 200
OUTPUTS = ("read", "refuting", "margins", "lengths_match", "good", "tables_match", "extensions_blocked",
           "palindromic_good", "conjecture_bound", "d", "closed_form", "example_349", "conditions_met",
           "conditions_total", "controls_passed", "controls_total", "test_passed")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading (rule 1)

def load(inputs):
    name, sha, size = EPRINT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
        raise Refused(f"{name}: not the pinned e-print")
    return gzip.decompress(data).decode("utf-8")


def section(tex, start, end):
    if tex.count(start) != 1:
        raise Refused(f"{start!r} is not printed exactly once")
    i = tex.index(start)
    j = tex.find(end, i + len(start))
    if j < 0:
        raise Refused(f"no {end!r} after {start!r}")
    return tex[i + len(start):j]


def word(text):
    """The paper's notation as a string of 0s and 1s."""
    s = re.sub(r"\\begin\{gather\*\}|\\end\{gather\*\}|\\scriptsize|\\normalsize|\\\\|\$|\s", "", text)
    s = s.rstrip(".")
    if not s or not re.fullmatch(r"(?:[01](?:\^\{\d+\})?)+", s):
        raise Refused(f"cannot read the word {s[:60]!r}")
    return "".join(b * int(k or 1) for b, k in re.findall(r"([01])(?:\^\{(\d+)\})?", s))


def certificates(tex):
    """{t: (bound n, strict, word)} from the appendix's two subsections."""
    out = {}
    exact = section(tex, "\\label{sec:Certificates3tp}", "\\subsection{Further lower bounds")
    further = section(tex, "\\label{sec:Certificates3tf}", "\\subsection{Good palindromic partitions}")
    for body, strict in ((exact, False), (further, True)):
        heads = list(re.finditer(r"\\paragraph\{\$\\vdw\(2; 3, (\d+)\)\s*(\\geq|>)\s*(\d+)\$\}", body))
        if not heads:
            raise Refused("no certificate headings")
        for k, h in enumerate(heads):
            t, rel, n = int(h.group(1)), h.group(2), int(h.group(3))
            if (rel == ">") != strict:
                raise Refused(f"t = {t}: unexpected relation {rel}")
            end = heads[k + 1].start() if k + 1 < len(heads) else len(body)
            chunk = body[h.end():end]
            chunk = chunk.split("\\normalsize")[0]
            if strict:
                m = re.search(r"\\begin\{gather\*\}(.*?)\\end\{gather\*\}", chunk, re.S)
                if not m:
                    raise Refused(f"t = {t}: no gather environment")
                text = m.group(1)
            else:
                parts = re.findall(r"\$\$(.*?)\$\$", chunk, re.S)
                if not parts:
                    raise Refused(f"t = {t}: no display math")
                text = "".join(parts)
            if t in out:
                raise Refused(f"t = {t} printed twice")
            out[t] = (n, strict, word(text))
    return out


def example_349(tex):
    chunk = section(tex, "An example of a good partition of the set $\\set{1,2,\\ldots,348}$ is as follows:",
                    "\\normalsize")
    return word("".join(re.findall(r"\$\$(.*?)\$\$", chunk, re.S)))


def table_bounds(tex, label):
    """{t: value} from the two-row tabular just before the label (a row of t, a row of values)."""
    mark = "\\label{" + label + "}"
    if tex.count(mark) != 1:
        raise Refused(f"{mark} is not printed exactly once")
    chunk = tex[:tex.index(mark)]
    chunk = chunk[chunk.rindex("\\begin{tabular}"):]
    chunk = chunk[:chunk.index("\\end{tabular}")]
    rows = [r for r in chunk.split("\\\\") if "&" in r]
    if len(rows) != 2:
        raise Refused(f"table {label}: {len(rows)} rows, not 2")
    cells = [[re.sub(r"\\textbf|[{}$\s]", "", x) for x in r.split("&")[1:]] for r in rows]
    if not all(re.fullmatch(r"\d+", x) for r in cells for x in r):
        raise Refused(f"table {label}: a cell is not a number")
    ts, vals = ([int(x) for x in r] for r in cells)
    if len(ts) != len(vals) or len(set(ts)) != len(ts):
        raise Refused(f"table {label}: rows differ in length")
    return dict(zip(ts, vals))


ANSATZ = "w_t := 9 + \\sum_{i=3}^{t-1} d \\cdot i"
CLOSED = "w_t = \\frac d2 t^2 - \\frac 32 d t + 9 - 2d < \\frac d2 t^2"


def conjecture(known, exact, further):
    """The improved conjecture's checks (rule 4): values within 77/46 t^2, the paper's d, and its Ansatz."""
    c = Fraction(77, 46)
    least = {t: v for t, v in known.items()}
    least.update(exact)
    least.update({t: v + 1 for t, v in further.items()})
    within = sum(1 for t, v in least.items() if v <= c * t * t)
    printed = dict(known)
    printed.update(exact)
    printed.update(further)
    if sorted(printed) != list(range(3, 40)):
        raise Refused(f"values for t = {sorted(printed)}, not 3 to 39")
    steps = {t: Fraction(printed[t] - printed[t - 1], t - 1) for t in range(4, 40)}
    d = max(steps.values())
    at = [t for t, s in steps.items() if s == d]
    return {"within": within, "total": len(least), "d": d, "d_at": at, "printed": printed}


def ansatz(d):
    """For t = 3 to 39: w_t from its definition, the printed closed form, and d/2 t^2."""
    rows = []
    for t in range(3, 40):
        w = 9 + d * sum(range(3, t))
        closed = d / 2 * t * t - Fraction(3, 2) * d * t + 9 - 2 * d
        rows.append({"t": t, "w_t": w, "closed": closed, "gap": w - closed, "below": w < d / 2 * t * t})
    return rows


def palindromic(tex):
    """[(t, m, half word)] from the palindromic table: a good palindromic partition of {1, ..., m} for each."""
    body = section(tex, "\\label{tab-pal}", "\\end{longtable}")
    body = body.split("\\endlastfoot", 1)[1]
    out, t = [], None
    for line in body.split("\n"):
        line = line.strip()
        if not line or line.startswith("\\hline"):
            continue
        line = re.sub(r"\\\\(\[-?\d+ex\])?$", "", line)
        cells = [c.strip() for c in line.split("&")]
        if len(cells) != 3:
            raise Refused(f"palindromic table: cannot read {line[:60]!r}")
        first, size, words = cells
        if first == "" and size == "":                  # a continuation of the last word
            if not out:
                raise Refused("palindromic table: a continuation with nothing before it")
            tt, m, w = out[-1]
            out[-1] = (tt, m, w + word(words))
            continue
        if first:
            t = int(first.strip("$"))
        sizes = size.strip("$").replace("\\geq", "").strip()
        texts = [x for x in re.split(r",\s*\\\s", words.strip("$"))]
        if sizes.startswith("("):
            ms = [int(x) for x in sizes.strip("()").split(",")]
        else:
            ms = [int(sizes)]
        if len(ms) != len(texts):
            raise Refused(f"palindromic table: t = {t}, sizes and words differ in number")
        for m, tx in zip(ms, texts):
            out.append((t, m, word(tx)))
    return out


# ---------------------------------------------------------------- good partitions (rule 2)

def has_progression(positions, length, n):
    """Whether the set of positions (1-based, within 1..n) contains an arithmetic progression of the given length."""
    s = set(positions)
    pos = sorted(s)
    if length <= 1:
        return bool(pos)
    for i, a in enumerate(pos):
        for b in pos[i + 1:]:
            d = b - a
            last = a + (length - 1) * d
            if last > n:
                break
            if all(a + k * d in s for k in range(2, length)):
                return True
    return False


def is_good(w, t):
    n = len(w)
    zeros = [i + 1 for i, c in enumerate(w) if c == "0"]
    ones = [i + 1 for i, c in enumerate(w) if c == "1"]
    return not has_progression(zeros, 3, n) and not has_progression(ones, t, n)


def is_good_naive(w, t):
    """Every progression a, a + d, ... checked directly, for the controls."""
    n = len(w)
    for length, bit in ((3, "0"), (t, "1")):
        for d in range(1, n):
            for a in range(1, n - (length - 1) * d + 1):
                if all(w[a + k * d - 1] == bit for k in range(length)):
                    return False
    return True


def palindrome_full(half, m):
    if len(half) != (m + 1) // 2:
        return None
    return half + (half[::-1] if m % 2 == 0 else half[:-1][::-1])


def vdw_exhaustive(t):
    """The least n with no good partition of {1, ..., n}, by enumeration."""
    n = 0
    while True:
        n += 1
        if not any(is_good(format(mask, f"0{n}b"), t) for mask in range(2 ** n)):
            return n


# ---------------------------------------------------------------- seeds, controls and the verdict

class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m


def plant_three_ap(w, stream):
    """A 0 placed where it completes a 3-term progression of 0s, at a seed-drawn choice of the possible places."""
    zeros = [i + 1 for i, c in enumerate(w) if c == "0"]
    cands = sorted({2 * b - a for i, a in enumerate(zeros) for b in zeros[i + 1:] if 2 * b - a <= len(w)
                    and w[2 * b - a - 1] == "1"})
    k = cands[stream.below(len(cands))]
    return w[:k - 1] + "0" + w[k:], k


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    tex = load(inputs)
    certs = certificates(tex)
    if sorted(certs) != list(range(20, 40)):
        raise Refused(f"certificates for t = {sorted(certs)}, not 20 to 39")
    ex349 = example_349(tex)
    t_known = table_bounds(tex, "tab:known3t")
    t_exact = table_bounds(tex, "tab:conj3t")
    t_further = table_bounds(tex, "tab:further3t")
    pals = palindromic(tex)

    res = {}
    for t, (n, strict, w) in sorted(certs.items()):
        m = n if strict else n - 1
        good = is_good(w, t)
        res[t] = {"bound": n, "strict": strict, "length": len(w), "needed": m, "length_ok": len(w) == m,
                  "good": good, "margin": m - t * t}
        if not strict:
            res[t]["extensions_good"] = [is_good(w + b, t) for b in "01"]
    cond = {
        "every word for t = 24 to 30 is a good partition of {1, ..., n - 1}":
            all(res[t]["length_ok"] and res[t]["good"] for t in TEST_T),
        "n - 1 >= t^2 for every t from 24 to 30": all(res[t]["margin"] >= 0 for t in TEST_T),
    }
    tables_ok = (sum(1 for t, v in t_exact.items() if t in certs and certs[t][0] == v and not certs[t][1]),
                 len(t_exact),
                 sum(1 for t, v in t_further.items() if t in certs and certs[t][0] == v and certs[t][1]),
                 len(t_further))
    pal_res = []
    for t, m, half in pals:
        full = palindrome_full(half, m)
        pal_res.append({"t": t, "m": m, "half": len(half), "good": bool(full) and is_good(full, t),
                        "palindrome": bool(full) and full == full[::-1]})
    pal_good = sum(1 for p in pal_res if p["good"] and p["palindrome"])
    conj = conjecture(t_known, t_exact, t_further)
    if ANSATZ in tex and CLOSED in tex:
        rows = ansatz(conj["d"])
        gaps = sum(1 for r in rows if r["gap"] == conj["d"] * (r["t"] - 1))
        below = sum(1 for r in rows if r["below"])
        closed = f"w_t - printed form = d(t - 1) at {gaps} of {len(rows)}; w_t < d t^2/2 at {below} of {len(rows)}"
    else:
        rows, closed = [], "not printed as read here"
    ex_good = len(ex349) == t_known.get(19, 0) - 1 and is_good(ex349, 19)

    ctl, ctl_detail = {}, {}
    ctl["exhaustive enumeration gives w(2;3,3) = 9 and w(2;3,4) = 18"] = (
        (vdw_exhaustive(3), vdw_exhaustive(4)) == (9, 18))
    stream = Stream(seed, "aks/controls")
    w24 = certs[24][2]
    planted, at = plant_three_ap(w24, stream)
    ctl["a 0 planted to complete a 3-term progression of 0s in the t = 24 word is caught"] = not is_good(planted, 24)
    ctl_detail["planted_at"] = at
    ctl["the t = 24 word shortened by one letter fails its length"] = len(w24[:-1]) != res[24]["needed"]
    ctl["a direct loop over all progressions agrees on the t = 24 and t = 30 words"] = all(
        is_good_naive(certs[t][2], t) == res[t]["good"] for t in (24, 30))

    ext_blocked = sum(1 for t in range(20, 31) if not any(res[t]["extensions_good"]))
    values = {
        "read": f"words for t = 20 to 39 ({len(certs)}), the 348-letter example, {len(pals)} palindromic partitions",
        "refuting": sum(1 for t in TEST_T if res[t]["length_ok"] and res[t]["good"] and res[t]["margin"] >= 0),
        "margins": " ".join(str(res[t]["margin"]) for t in TEST_T),
        "lengths_match": sum(1 for r in res.values() if r["length_ok"]),
        "good": sum(1 for r in res.values() if r["good"]),
        "tables_match": f"{tables_ok[0]} of {tables_ok[1]}; {tables_ok[2]} of {tables_ok[3]}",
        "extensions_blocked": ext_blocked,
        "palindromic_good": pal_good,
        "conjecture_bound": f"{conj['within']} of {conj['total']}",
        "d": f"{conj['d'].numerator}/{conj['d'].denominator} at t = {', '.join(map(str, conj['d_at']))}",
        "closed_form": closed,
        "example_349": int(ex_good),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": EPRINT[0], "sha256": EPRINT[1], "bytes": EPRINT[2]}, "conditions": cond,
              "controls": ctl, "control_detail": ctl_detail, "certificates": {str(t): r for t, r in res.items()},
              "tables": {"known": t_known, "conjectured": t_exact, "further": t_further}, "palindromic": pal_res,
              "conjecture": {"within": conj["within"], "total": conj["total"], "d": str(conj["d"]),
                             "d_at": conj["d_at"]},
              "ansatz": [{k: (str(v) if isinstance(v, Fraction) else v) for k, v in r.items()} for r in rows],
              "example_349": {"length": len(ex349), "good": ex_good}}
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
        sys.exit(f"aks: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
