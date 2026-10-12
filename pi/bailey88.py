#!/usr/bin/env python3
"""Bailey's 29,360,000 digits of pi (1986, Cray-2), checked against pi computed afresh, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:00353b93b3e038b8) is from Bailey, "The
computation of pi to 29,360,000 decimal digits using Borweins' quartically convergent algorithm", Mathematics of
Computation 50(181), 283-296 (1988): "The author has implemented Borweins' quartically convergent algorithm for 1/pi,
using a prime modulus transform multi-precision technique, to compute over 29,360,000 digits of the decimal expansion
of pi."

Its registered test: refuted if, with pi computed afresh beyond 29,360,000 decimals by two independent methods that
agree, any digit of the seven 1000-digit blocks the paper's appendix prints (decimals 1-1,000, 4,999,001-5,000,000,
9,999,001-10,000,000, 14,999,001-15,000,000, 19,999,001-20,000,000, 24,999,001-25,000,000 and 29,359,001-29,360,000)
differs from pi's, or if the counts of the digits 0 to 9 among decimals 1-29,360,000 differ from Table 1's: 2935072,
2936516, 2936843, 2935205, 2938787, 2936197, 2935504, 2934083, 2935698, 2936095.

The one input is the claim's data of record, the author's own copy of the paper (bailey1988_pi.pdf, from his site; the
AMS PDF sits behind a browser check no runner passes), read as data: its content streams are decompressed with zlib
and the strings it shows are read by a small parser of this module's own. Standard library and gcc with GMP, in the
buildpack-deps image. Every rule below was fixed before any seed existed; the seed is not used, as nothing here is
random.

1. The paper's numbers. The PDF must have its committed sha256. Only the pages' content streams are read, and every
   page must end with its own page number, which is dropped. Its appendix must print seven blocks under the headings
   "Initial 1000 digits:" and "Digits a to b:", in that order, at the seven places the test names, each of exactly
   1000 digits (the first after "3."; a block runs on over a page break and ends at any other text); its Table 1 must
   print, under the header Digit, Count, Deviation, Z-score, the rows for the digits 0 to 9 in order, with the ten
   counts the test names. Otherwise the run is refused.
2. Pi, twice. pi/bailey88.c, compiled here with gcc -O2 against GMP, computes floor(pi 10^N) for N = 29,360,100 by
   the Chudnovskys' series (binary splitting) and, separately, by the Gauss-Legendre iteration in binary fixed point
   (both described in the C file). The two results must agree in at least the first 29,360,050 decimals, and both
   must begin with the 50 decimals of PI50 below; otherwise the run is refused.
3. The test's two conditions: the 7,000 printed digits equal pi's at their places; the counts of each digit 0 to 9 among
   decimals 1 to 29,360,000 equal Table 1's. test_passed is 1 if both hold.
4. Beside the test: Table 1's deviations (count - 2,936,000) and z-scores (deviation / sqrt(29,360,000 x 0.1 x 0.9),
   to four places) recomputed from the counts and compared with the printed ones; the number of leading decimals in
   which the two methods agree; the Gauss-Legendre iterations; and the SHA-256 of decimals 1 to 29,360,000, so that
   another run can be compared digit for digit.

What it cannot check: the computation itself (the Cray-2's run, its prime modulus transform arithmetic and its
quadratic check), only what it printed; and whether the AMS's published version prints exactly what the author's copy
does (its abstract's wording differs slightly).

Writes results/outputs.json and results/detail.json. Run with: python3 pi/bailey88.py
"""

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = ("bailey1988_pi.pdf", "3a4d9339aa8856bc2250e71611e06945f858922c05fc81501013f86047bebb4a")
N_COMPUTE, N_AGREE, N_USE = 29_360_100, 29_360_050, 29_360_000
PI50 = "14159265358979323846264338327950288419716939937510"
BLOCKS = (1, 4_999_001, 9_999_001, 14_999_001, 19_999_001, 24_999_001, 29_359_001)
BLOCK_LEN = 1000
TABLE1 = (2935072, 2936516, 2936843, 2935205, 2938787, 2936197, 2935504, 2934083, 2935698, 2936095)
HEADER = ("Digit", "Count", "Deviation", "Z-score")
OUTPUTS = ("decimals", "methods_agree", "agm_iterations", "blocks_matched", "block_digits_wrong", "counts",
           "counts_as_printed", "table1_matched", "pi_digest", "test_passed")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading the PDF (rule 1)

def page_contents(data):
    """The object numbers of the pages' content streams, in the order the page objects name them."""
    nums = []
    for m in re.finditer(rb"/Contents\s*(\[[^\]]*\]|\d+\s+0\s+R)", data):
        nums += [int(x) for x in re.findall(rb"(\d+)\s+0\s+R", m.group(1))]
    return nums


def content_streams(data):
    """The pages' content streams, decompressed: [(object number, bytes)]. Only these are read as text; the PDF's other
    streams (its Type 3 glyphs among them) are not text and are left alone."""
    streams = dict(pdf_streams(data))
    nums = page_contents(data)
    missing = [n for n in nums if n not in streams]
    if not nums or missing:
        raise Refused(f"content streams not found: {missing or 'none named'}")
    return [(n, streams[n]) for n in nums]


def pdf_streams(data):
    """Every stream of the PDF in file order, decompressed when FlateDecode: [(object number, bytes)]."""
    out = []
    for m in re.finditer(rb"(\d+)\s+0\s+obj\b", data):
        start = m.end()
        s = data.find(b"stream", start)
        e = data.find(b"endobj", start)
        if s < 0 or (0 <= e < s):
            continue
        head = data[start:s]
        lm = re.search(rb"/Length\s+(\d+)(\s+0\s+R)?", head)
        if not lm:
            continue
        if lm.group(2):
            ref = re.search(rb"(?<![0-9])" + lm.group(1) + rb"\s+0\s+obj\s*(\d+)\s*endobj", data)
            if not ref:
                continue
            length = int(ref.group(1))
        else:
            length = int(lm.group(1))
        p = s + len(b"stream")
        if data[p:p + 2] == b"\r\n":
            p += 2
        elif data[p:p + 1] in (b"\n", b"\r"):
            p += 1
        raw = data[p:p + length]
        if b"/FlateDecode" in head:
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                continue
        out.append((int(m.group(1)), raw))
    return out


ESCAPES = {ord("n"): "\n", ord("r"): "\r", ord("t"): "\t", ord("b"): "\b", ord("f"): "\f", ord("("): "(",
           ord(")"): ")", ord("\\"): "\\"}


def read_string(s, i):
    """A PDF literal string starting at s[i] == '(': (text, index after its closing parenthesis)."""
    depth, i, out = 1, i + 1, []
    while i < len(s):
        c = s[i]
        if c == 0x5C:  # backslash
            nxt = s[i + 1] if i + 1 < len(s) else None
            if nxt in ESCAPES:
                out.append(ESCAPES[nxt])
                i += 2
            elif nxt is not None and 0x30 <= nxt <= 0x37:
                j = i + 1
                while j < len(s) and j < i + 4 and 0x30 <= s[j] <= 0x37:
                    j += 1
                out.append(chr(int(s[i + 1:j], 8)))
                i = j
            elif nxt in (0x0A, 0x0D):
                i += 2
            else:
                i += 1
            continue
        if c == 0x28:
            depth += 1
        elif c == 0x29:
            depth -= 1
            if depth == 0:
                return "".join(out), i + 1
        out.append(chr(c))
        i += 1
    raise Refused("an unterminated string in a content stream")


def text_chunks(stream):
    """The strings a content stream shows, in order: one chunk for each Tj, ' or " (its string) and each TJ (its
    array's strings joined, the spacing numbers dropped)."""
    chunks, operands, array = [], [], None
    i, n = 0, len(stream)
    while i < n:
        c = stream[i]
        if c == 0x28:
            text, i = read_string(stream, i)
            (array if array is not None else operands).append(text)
            continue
        if c == 0x5B:
            array, i = [], i + 1
            continue
        if c == 0x5D:
            operands.append("".join(array or []))
            array, i = None, i + 1
            continue
        if c == 0x25 and array is None:  # a comment, to the end of the line
            while i < n and stream[i] not in (0x0A, 0x0D):
                i += 1
            continue
        if chr(c).isalpha() or c in (0x27, 0x22):
            j = i + 1
            if chr(c).isalpha():
                while j < n and (chr(stream[j]).isalnum() or stream[j] in (0x2A,)):
                    j += 1
            op = stream[i:j]
            if op in (b"Tj", b"'", b'"', b"TJ") and operands:
                chunks.append(operands[-1])
            operands = []
            i = j
            continue
        i += 1
    return chunks


def page_texts(streams):
    """Each page's strings without its page number: every page of the author's copy ends with its own number (1 to 16),
    which is checked and dropped, so that a block running over a page break does not take it in."""
    pages = []
    for k, (_, stream) in enumerate(streams, 1):
        chunks = text_chunks(stream)
        if not chunks or chunks[-1].strip() != str(k):
            raise Refused(f"page {k} does not end with its page number")
        pages.append(chunks[:-1])
    return pages


def appendix_blocks(streams):
    """{first decimal: digits} for every block under an appendix heading, a block ending at the next heading or at the
    end of the paper (it runs on over a page break)."""
    blocks = {}
    current = None
    for chunks in page_texts(streams):
        for chunk in chunks:
            flat = chunk.replace(" ", "")
            m = re.fullmatch(r"Digits([\d,]+)to([\d,]+):?", flat)
            if flat == "Initial1000digits:":
                current = 1
                blocks[current] = []
            elif m:
                current = int(m.group(1).replace(",", ""))
                blocks[current] = []
            elif current is not None and re.fullmatch(r"\d+", flat):
                blocks[current].append(flat)
            elif current is not None and flat not in ("3.", ":"):
                current = None  # any other text ends a block
    return {k: "".join(v) for k, v in blocks.items()}


def table1_rows(streams):
    """Table 1's rows (digit, count, deviation, z-score as printed), from the page whose header is Digit, Count,
    Deviation, Z-score followed by the rows for 0 to 9."""
    for page in page_texts(streams):
        chunks = [c.strip() for c in page]
        joined = []
        k = 0
        while k < len(chunks):  # "Coun" "t" is how the header's second word is set
            if chunks[k] == "Coun" and k + 1 < len(chunks) and chunks[k + 1] == "t":
                joined.append("Count")
                k += 2
            else:
                joined.append(chunks[k])
                k += 1
        for h in range(len(joined) - len(HEADER)):
            if tuple(joined[h:h + len(HEADER)]) != HEADER:
                continue
            rows = joined[h + len(HEADER): h + len(HEADER) + 40]
            if len(rows) == 40 and [rows[4 * d] for d in range(10)] == [str(d) for d in range(10)]:
                return [tuple(rows[4 * d: 4 * d + 4]) for d in range(10)]
    return None


def read_paper(path):
    with open(path, "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != INPUT[1]:
        raise Refused(f"{INPUT[0]}: sha256 {got}, not the committed {INPUT[1]}")
    streams = content_streams(data)
    blocks = appendix_blocks(streams)
    if sorted(blocks) != list(BLOCKS):
        raise Refused(f"the appendix's blocks start at {sorted(blocks)}, not {list(BLOCKS)}")
    for start, digits in blocks.items():
        if len(digits) != BLOCK_LEN:
            raise Refused(f"the block from decimal {start} has {len(digits)} digits, not {BLOCK_LEN}")
    rows = table1_rows(streams)
    if rows is None:
        raise Refused("no Table 1 (Digit, Count, Deviation, Z-score, rows 0 to 9) in the paper")
    if tuple(int(r[1]) for r in rows) != TABLE1:
        raise Refused(f"Table 1 prints the counts {[r[1] for r in rows]}, not the test's")
    return blocks, rows


# ---------------------------------------------------------------- pi, twice (rule 2)

def build(results):
    os.makedirs(os.path.join(results, "build"), exist_ok=True)
    exe = os.path.join(results, "build", "bailey88")
    subprocess.run(["gcc", "-O2", "-o", exe, os.path.join(HERE, "bailey88.c"), "-lgmp", "-lm"], check=True)
    return exe


def two_pis(exe, n, results):
    files = {m: os.path.join(results, "build", f"pi_{m}.txt") for m in ("chud", "agm")}
    procs = {m: subprocess.Popen([exe, m, str(n), files[m]], stderr=subprocess.PIPE, text=True) for m in files}
    notes = {}
    for m, p in procs.items():
        _, err = p.communicate()
        if p.returncode != 0:
            raise Refused(f"bailey88 {m} failed: {err.strip()}")
        notes[m] = err.strip()
    texts = {}
    for m, path in files.items():
        with open(path, encoding="ascii") as f:
            texts[m] = f.read().strip()
        os.remove(path)
    return texts, notes


def agreement(a, b):
    """The number of leading characters a and b share."""
    lo, hi = 0, min(len(a), len(b))
    if a[:hi] == b[:hi]:
        return hi
    while hi - lo > 1:  # a[:lo] == b[:lo] and a[:hi] != b[:hi]
        mid = (lo + hi) // 2
        if a[:mid] == b[:mid]:
            lo = mid
        else:
            hi = mid
    return lo


# ---------------------------------------------------------------- the run

def z_text(count, d=None):
    """A z-score as Table 1 prints it: (count - d/10) / sqrt(d x 0.1 x 0.9), to four places."""
    d = N_USE if d is None else d
    return f"{(count - d // 10) / math.sqrt(d * 0.1 * 0.9):.4f}"


def run(seed, inputs="inputs", results="results", log=print):
    started = time.monotonic()
    blocks, rows = read_paper(os.path.join(inputs, INPUT[0]))
    exe = build(results)
    texts, notes = two_pis(exe, N_COMPUTE, results)
    for m, t in texts.items():
        if len(t) != N_COMPUTE + 1 or t[0] != "3" or t[1:51] != PI50:
            raise Refused(f"{m}: not floor(pi 10^{N_COMPUTE}) as expected ({len(t)} characters, {t[:12]}...)")
    agree = agreement(texts["chud"], texts["agm"]) - 1  # decimals, after the leading 3
    if agree < N_AGREE:
        raise Refused(f"the two methods agree in only {agree} decimals")
    decimals = texts["chud"][1:N_USE + 1]
    del texts
    log(f"bailey88: pi to {N_COMPUTE} decimals twice, agreeing in {agree}; {round(time.monotonic() - started)} s")
    wrong, matched = 0, 0
    for start, digits in blocks.items():
        ref = decimals[start - 1: start - 1 + BLOCK_LEN]
        w = sum(1 for x, y in zip(digits, ref) if x != y)
        wrong += w
        matched += 1 if w == 0 else 0
    counts = [decimals.count(str(d)) for d in range(10)]
    as_printed = sum(1 for c, p in zip(counts, TABLE1) if c == p)
    table1 = 0
    for d, (digit, count, dev, z) in enumerate(rows):
        table1 += (int(count) == counts[d]) + (dev == str(counts[d] - N_USE // 10)) + (z == z_text(counts[d]))
    iters = re.search(r"agm: (\d+) iterations", notes.get("agm", ""))
    out = {
        "decimals": N_COMPUTE, "methods_agree": agree, "agm_iterations": int(iters.group(1)) if iters else -1,
        "blocks_matched": matched, "block_digits_wrong": wrong, "counts": ", ".join(map(str, counts)),
        "counts_as_printed": as_printed, "table1_matched": table1,
        "pi_digest": hashlib.sha256(decimals.encode("ascii")).hexdigest()[:16],
        "test_passed": int(wrong == 0 and matched == len(BLOCKS) and as_printed == 10),
    }
    detail = {"values": out, "table1_printed": [list(r) for r in rows],
              "table1_recomputed": [[str(d), str(counts[d]), str(counts[d] - N_USE // 10), z_text(counts[d])]
                                    for d in range(10)],
              "blocks": {str(k): {"printed_head": v[:20], "pi_head": decimals[k - 1:k + 19]} for k, v in blocks.items()},
              "notes": notes, "seconds": round(time.monotonic() - started, 1)}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True)
        f.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed, log=lambda s: print(s, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"pi/bailey88.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
