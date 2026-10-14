#!/usr/bin/env python3
"""Herwig, Heule, van Lambalgen & van Maaren's Cyclic Zipper method: the seven Van der Waerden lower bounds it
improved, each certificate rebuilt from the printed prime and number of zippings and checked in full.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:56ae1de685a5124a) is from Herwig, Heule,
van Lambalgen and van Maaren, "A New Method to Construct Lower Bounds for Van der Waerden Numbers" (The Electronic
Journal of Combinatorics 14, #R6, 2007): "We present the Cyclic Zipper Method, a procedure to construct lower bounds
for Van der Waerden numbers. Using this method we improved seven lower bounds."

Its registered test: refuted if, for one of the seven bounds W(r, k) > n that Table 3 prints in bold, the certificate
the Cyclic Zipper method builds from the printed prime p and number of zippings z (the power residue colouring of 1..p
with the least primitive root, as rho_37 = 2; zipped z times as Section 4.3 defines, shifting by p; repeated k - 1
times, one number added) has a k-term progression in one subset for every colouring of the numbers 1 + jp (1 in C1
and the added number in Cr in the text), or n != (k - 1) 2^z p + 1, or the rows exceeding Table 1's bounds are not
those seven.

Standard library and the image's gcc: the progression scans are C (vdw/hhlm.c, compiled here with -O3). The input is
the claim's data of record, the paper as the journal serves it (a PDF of 18 pages), checked against its SHA-256 and
size and read in memory as data; nothing in it is run. Every rule below was fixed before any certificate was built or
any progression counted.

1. Reading. The pages in the order of the PDF's page tree, each page's content streams (Flate, the /Length direct or
   an indirect reference) decompressed. Each string of a Tj operator (or the strings of a TJ array, joined) is one
   token, in the font of the last Tf, its resource name looked up in the page's font dictionary and its BaseFont read
   from the font object. Raw character codes are kept: in the math italic (CMMI) code 59 is a comma, code 62 ">" and
   code 26 rho; in the roman (CMR) code 123 is an en dash, printed here as "{"; in the symbol font (CMSY) code 110 is
   the backslash of r\\k. Each of the paper's Tables 1 to 4, as transcribed below (TABLE1 to TABLE4, rendered by
   table_tokens), must appear exactly once as consecutive tokens of one page, and the fonts must be as printed: in
   Table 3 the result of each row in a bold face (a BaseFont "+CMBX") exactly when the transcription marks it bold, in
   Table 4 the entries likewise, Table 1's entries never, the column and row labels of Tables 1 and 4 always. The
   paper's statements (STATEMENTS) must be found in the page texts with the spaces removed (ligatures fi, ff, fl, ffi
   and the math codes above mapped). The run is refused otherwise, as a reading error.
2. The method (Sections 3.2.2, 4.2, 4.3 and 5), for a row (r, k, p, z, n):
   a. rho, the least primitive root of p (the paper's example: rho_37 = 2); p must be prime and r must divide p - 1,
      or the row fails.
   b. The power residue colouring of 1..p (Eq. 1): j in 2..p lies in C_i, where rho^e = j - 1 (mod p) with e in
      1..p - 1 and i = ((e - 1) mod r) + 1, that is rho^(i + qr) (mod p) + 1 for q = 0..(p - 1)/r - 1; and
      "Additionally, number 1 will be put in C1."
   b'. The labels (Section 3.2.1): "For visualization purposes we assume permutation pi is applied for all
      PW(r, k, n)", a point symmetric certificate's classes relabelled so that the reverse of C_i (j := n + 2 - j for
      j = 2..n, n odd) is C_(r+1-i), and Section 4.3 zips a cPW. Where the colouring of 2b is point symmetric (the
      reverse maps each class onto one class, an involution without a fixed class), pi is applied before zipping:
      the classes in increasing order, the first unlabelled one takes the smallest free label i and its partner
      r + 1 - i (for 37, the third and fourth rows interchanged, as Section 4.2 says). Otherwise the labels of 2b
      stand. Number 1 keeps C1 either way.
   c. Zipping (Section 4.3), z times, a certificate of length m giving one of length 2m: spreading, j := 2j - 1;
      turning, C**_i := C*_(r+1-i); shifting, j := j - p (mod 2m), in 1..2m; merging, C****_i := C*_i u C***_i. The
      shift is p each time ("using the original certificate length to shift", Section 4.3, and Figure 8). The merged
      classes must cover 1..2m once each (refused otherwise).
   d. Repetition (Definition 3.2): k - 1 copies of the cyclic certificate of length N = 2^z p, the number y in the
      class of ((y - 1) mod N) + 1, and one additional number, (k - 1)N + 1, added to C_r ("Following Rabung [13],
      one additional number can be added to the set Cr").
3. The free numbers. The numbers whose class the method takes from number 1's place in C1 (through the zips and the
   copies), and the added number: these are exactly the numbers 1 + jp, j = 0..(k - 1)2^z, which the run requires.
   The text's own certificate gives them the classes of 2; the test lets them take any class. Every other number's
   class is fixed by 2.
4. The check of a row. (i) n = (k - 1) 2^z p + 1 for the printed n. (ii) For each free number y and class c, c is
   forbidden to y if some k-term progression through y has its other k - 1 numbers fixed and in C_c (hhlm.c forbid; a
   progression holding two free numbers has a difference divisible by p > k, so all its numbers are free, and the run
   requires hhlm.c's count of progressions mixing two free numbers with a fixed one to be 0); a progression of free
   numbers only must not lie in one class. A depth-first search over the free numbers in increasing order, each
   trying the class the text gives it first and then C_1 to C_r, finds the first colouring meeting both, or shows
   that none does (refused beyond NODE_LIMIT nodes). (iii) With the colouring found, every progression x, x + d, ...,
   x + (k - 1)d with x >= 1, d >= 1 and x + (k - 1)d <= n is examined (hhlm.c scan), and the number in one class must
   be 0. The row holds if (i) holds, a colouring is found and (iii) finds none. The text's own certificate is valid
   exactly when the search's first colouring is the text's own and (iii) finds none; otherwise the run names one
   progression in one class in it.
5. The test's three conditions: the rows of Table 3 whose printed bound n exceeds Table 1's bound for the same r and k
   (a printed "> m" bounds W(r, k) by m, a known value W by W - 1) are exactly the seven in bold; each of the seven
   has n = (k - 1) 2^z p + 1; and each of the seven holds (4). test_passed is 1 if all three hold.
6. Beside the test, none of it counted: the other eight rows of Table 3 checked the same way; the text's own
   certificate for all fifteen; the seven checked again with the labels of 2b (no pi), the reading the first program
   took (raw_reading); Table 4's entries for r = 2, 4 and 6 against Table 3's results, as bounds (a known value W
   printed without ">" bounds W(r, k) by W - 1); the least primitive roots; and the number of progressions examined.

Controls (controls_passed counts those that behave as stated): the power residue colouring of 37 over 4 rows with
rho = 2, the least primitive root of 37, is the paper's Table 2, entry for entry; its pi interchanges the third and
fourth rows and no others (Section 4.2: "Notice that the third and fourth row are interchanged to show the point
symmetry"); hhlm.c's scan and forbid agree with
a direct enumeration in Python on 30 seed-drawn colourings (lengths 20 to 90, 2 to 4 classes, k from 3 to 5, some
numbers free); a progression in one class planted at a seed-drawn place in the text's own certificates for W(2, 8),
W(4, 5) and W(2, 9) is found by the scan; the certificates for W(2, 4), W(2, 5) and W(4, 3), of 34, 177 and 75
numbers, hold no progression and none extends by one number in any class, as the known values 35, 178 and 76 (Table
1) require; on 10 seed-drawn colourings of 30 to 60 numbers whose free numbers are 1, 1 + q and 1 + 2q for a prime q
between n/3 and (n - 1)/2 (so that, as in the certificates, a progression with two free numbers has only free
numbers), the search finds a colouring exactly when one of the r^3 does by exhaustion; and for every prime of
Table 3, rho's powers run through all p - 1 residues and no smaller number's do.

Changed after the trial (14 October; the rules were first committed at 7bfd00d). A trial in the reference runner,
under a seed of Imago's own, showed two faults. (1) The first program turned the classes as 2b labels them (rule
2b' was not there). With those labels, the seven held in 2 of 7: W(4,5), W(4,6), W(4,7), W(6,5) and W(6,6), the
rows with r = 4 or 6 and z >= 1, failed, with 5,478,608 progressions in one class among them, the first of each a
run of k consecutive numbers; the other ten rows held. Reading the paper again, its point symmetric certificates are
labelled with pi applied (Section 3.2.1, and Section 4.2 for 37), and the certificate Section 4.3 zips is a cPW, so
the turning acts on those labels. For r = 2 the turning swaps the two classes under any labels, so nothing changes;
for r = 4 and 6 it maps each class to its point symmetric partner, not to C_(r+1-i) of 2b. Rule 2b' was added and
the first reading is kept beside (raw_reading), not counted. This change was made after the trial's outcome was
seen. (2) Table 4 prints the known values 35, 178 and 76 without ">", and the first program compared them with
Table 3's bounds as printed, so 12 of 15 agreed; they are now compared as bounds (rule 6).

What it cannot check: that Table 1 held the best bounds known in 2005 and 2006 (its note 4 marks some as unpublished
bounds that Rabung's method could establish), the paper's account of how the primes were found, and its remark that
zipping is not effective for odd r. The authors' certificates, on their website in 2007, are not used.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 vdw/hhlm.py
"""

import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = ("hhlm-ejc-14-r6.pdf", "8c927b6a44dbba223e7d834bcc20c298d2926f5f05caaa1d596aa0e63562d8da", 662312)
PAGES = 18
FREE = 255
NODE_LIMIT = 1_000_000
LIMIT = 200

# Table 3: (r, k, prime, zippings, printed bound n, the result in bold), in the order printed; W(2, 3) has dashes.
TABLE3 = ((2, 4, 11, 0, 34, False), (2, 5, 11, 2, 177, False), (2, 6, 113, 1, 1131, False),
          (2, 7, 617, 0, 3703, False), (2, 8, 821, 1, 11495, True), (2, 9, 2579, 1, 41265, True),
          (4, 3, 37, 0, 75, False), (4, 4, 349, 0, 1048, False), (4, 5, 2213, 1, 17705, True),
          (4, 6, 9133, 1, 91331, True), (4, 7, 32789, 1, 393469, True), (6, 3, 103, 0, 207, False),
          (6, 4, 3259, 0, 9778, False), (6, 5, 3967, 2, 63473, True), (6, 6, 31699, 2, 633981, True))
# Table 1: for each r, its entries for k = 3, 4, ...: (value, printed with ">", reference, footnote mark).
TABLE1 = {2: ((9, False, 3, None), (35, False, 3, None), (178, False, 16, None), (1131, True, 11, None),
              (3703, True, 13, None), (7484, True, 13, None), (27113, True, 13, None)),
          3: ((27, False, 3, None), (292, True, 13, None), (965, True, 13, "3"), (8886, True, 13, None),
              (43855, True, 13, None), (238400, True, 13, "4")),
          4: ((76, False, 1, None), (1048, True, 13, None), (10437, True, 13, None), (90306, True, 13, None),
              (387967, True, 13, "4")),
          5: ((125, True, 4, None), (2254, True, 13, None), (24045, True, 13, None), (246956, True, 13, "4")),
          6: ((207, True, 13, None), (9778, True, 13, None), (56693, True, 13, "4"), (600486, True, 13, "4"))}
# Table 4: for each r, its entries for k = 3, 4, ...: (value, printed with ">", in bold).
TABLE4 = {2: ((9, False, False), (35, False, False), (178, False, False), (1131, True, False), (3703, True, False),
              (11495, True, True), (41265, True, True)),
          3: ((27, False, False), (292, True, False), (1209, True, False), (8886, True, False), (43855, True, False),
              (238400, True, False)),
          4: ((76, False, False), (1048, True, False), (17705, True, True), (91331, True, True),
              (393469, True, True)),
          5: ((125, True, False), (2254, True, False), (24045, True, False), (246956, True, False)),
          6: ((207, True, False), (9778, True, False), (63473, True, True), (633981, True, True))}
# Table 2: the power residue colouring of 37 over 4 rows, C_i's entries for q = 0..8.
TABLE2 = ((3, 33, 32, 16, 19, 30, 21, 25, 15), (5, 28, 26, 31, 37, 22, 4, 12, 29), (9, 18, 14, 24, 36, 6, 7, 23, 20),
          (17, 35, 27, 10, 34, 11, 13, 8, 2))
STATEMENTS = (
    "Using this method we improved seven lower bounds.",
    "Following Rabung [13], one additional number can be added to the set Cr.",
    "We denote by ρp the primitive root of unity of a prime p.",
    "(ρ37 = 2)",
    "Additionally, number 1 will be put in C1.",
    "Spreading: A partition of double length is created by setting j := 2j − 1",
    "Turning: The partition is turned upside down",
    "Shifting: The partition is shifted left for the length of a certificate by setting j := j − n (mod 2n)",
    "Merging: Form a partition by merging the subsets resulting from the spreading and the shifting step",
    "using the original certificate length to shift",
    "Validate: Check if the zipped certificate is cyclic itself.",
    "Repeat: Create a repetitive cyclic certificate by appending the present certificate",
    "The lower bounds in bold are improvements over the existing lower bounds.",
    "certificates proving the improved lower bounds.",
    "Using this procedure we determined seven improved lower bounds",
)
EXACT = {(2, 4): 35, (2, 5): 178, (4, 3): 76}
PLANT_IN = ((2, 8), (4, 5), (2, 9))
SCAN_CONTROLS = 30
SEARCH_CONTROLS = 10
OUTPUTS = ("statements", "tables", "improved", "lengths", "roots", "seven", "progressions", "monochromatic", "free",
           "text_own", "others", "raw_reading", "exact", "table4", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading the PDF (rule 1)

def read_input(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


class Pdf:
    """The objects of a PDF without object streams, found by their 'N 0 obj' headers."""

    def __init__(self, data):
        self.data = data
        self.at = {}
        for m in re.finditer(rb"(?<![^\r\n])(\d+) 0 obj\b", data):
            num = int(m.group(1))
            if num in self.at:
                raise Refused(f"object {num} is defined twice")
            self.at[num] = m.end()

    def body(self, num):
        if num not in self.at:
            raise Refused(f"no object {num}")
        start = self.at[num]
        end = self.data.find(b"endobj", start)
        if end < 0:
            raise Refused(f"object {num} has no endobj")
        return self.data[start:end]

    def stream(self, num):
        body = self.body(num)
        m = re.match(rb"\s*<<(.*?)>>\s*stream\r?\n", body, re.S)
        if not m:
            raise Refused(f"object {num} is not a stream")
        head = m.group(1)
        ref = re.search(rb"/Length\s+(\d+)\s+0\s+R", head)
        if ref:
            got = re.fullmatch(rb"\s*(\d+)\s*", self.body(int(ref.group(1))))
            if not got:
                raise Refused(f"object {num}: its /Length is not a number")
            length = int(got.group(1))
        else:
            direct = re.search(rb"/Length\s+(\d+)", head)
            if not direct:
                raise Refused(f"object {num}: no /Length")
            length = int(direct.group(1))
        start = self.at[num] + m.end()
        raw = self.data[start:start + length]
        if b"/FlateDecode" not in head:
            raise Refused(f"object {num}: not Flate")
        try:
            return zlib.decompress(raw)
        except zlib.error as e:
            raise Refused(f"object {num}: {e}")

    def dict_refs(self, text):
        return {k.decode(): int(v) for k, v in re.findall(rb"/(\w+)\s+(\d+)\s+0\s+R", text)}

    def pages(self):
        """(contents, font names) for each page, in the order of the page tree."""
        root = re.search(rb"/Root\s+(\d+)\s+0\s+R", self.data[self.data.rfind(b"trailer"):])
        if not root:
            raise Refused("no /Root in the trailer")
        cat = self.body(int(root.group(1)))
        top = re.search(rb"/Pages\s+(\d+)\s+0\s+R", cat)
        if not top:
            raise Refused("no /Pages in the catalogue")
        out = []

        def walk(num, depth=0):
            if depth > 20:
                raise Refused("the page tree is too deep")
            body = self.body(num)
            if re.search(rb"/Type\s*/Pages\b", body):
                kids = re.search(rb"/Kids\s*\[([^\]]*)\]", body)
                if not kids:
                    raise Refused(f"pages node {num} has no /Kids")
                for kid in re.findall(rb"(\d+)\s+0\s+R", kids.group(1)):
                    walk(int(kid), depth + 1)
            elif re.search(rb"/Type\s*/Page\b", body):
                out.append(self.page(num, body))
            else:
                raise Refused(f"object {num} in the page tree is neither /Page nor /Pages")

        walk(int(top.group(1)))
        return out

    def page(self, num, body):
        cont = re.search(rb"/Contents\s*(\[[^\]]*\]|\d+\s+0\s+R)", body)
        if not cont:
            raise Refused(f"page {num} has no /Contents")
        streams = [int(x) for x in re.findall(rb"(\d+)\s+0\s+R", cont.group(1))]
        fonts = {}
        font = re.search(rb"/Font\s*(<<.*?>>|\d+\s+0\s+R)", body, re.S)
        if font:
            text = font.group(1)
            if text.startswith(b"<<"):
                refs = self.dict_refs(text)
            else:
                refs = self.dict_refs(self.body(int(text.split()[0])))
            for name, obj in refs.items():
                base = re.search(rb"/BaseFont\s*/([^\s/<>\[\]]+)", self.body(obj))
                if not base:
                    raise Refused(f"font {name} (object {obj}) has no /BaseFont")
                fonts[name] = base.group(1).decode("latin-1")
        content = b"\n".join(self.stream(s) for s in streams)
        return content, fonts


TOKEN = re.compile(rb"\[((?:\((?:\\.|[^\\)])*\)|[^\]])*)\]\s*TJ|\(((?:\\.|[^\\)])*)\)\s*Tj|/([^\s/\[\]<>()]+)\s+"
                   rb"-?[\d.]+\s+Tf", re.S)
STRING = re.compile(rb"\(((?:\\.|[^\\)])*)\)", re.S)


def unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == 0x5C and i + 1 < len(s):
            nxt = s[i + 1]
            if 0x30 <= nxt <= 0x37:
                j, v = i + 1, 0
                while j < len(s) and j < i + 4 and 0x30 <= s[j] <= 0x37:
                    v = v * 8 + s[j] - 0x30
                    j += 1
                out.append(v & 0xFF)
                i = j
                continue
            out.append({0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}.get(nxt, nxt))
            i += 2
            continue
        out.append(c)
        i += 1
    return bytes(out)


def page_tokens(content, fonts):
    """The page's tokens in order: (text, BaseFont), the text the raw codes as latin-1."""
    out, font = [], None
    for t in TOKEN.finditer(content):
        if t.group(3) is not None:
            name = t.group(3).decode("latin-1")
            if name not in fonts:
                raise Refused(f"font {name} is not in the page's resources")
            font = fonts[name]
            continue
        if t.group(2) is not None:
            raw = unescape(t.group(2))
        else:
            raw = b"".join(unescape(p.group(1)) for p in STRING.finditer(t.group(1)))
        if font is None:
            raise Refused("text before any font")
        out.append((raw.decode("latin-1"), font))
    return out


def family(font):
    m = re.search(r"\+?(CMMI|CMSY|CMBX|CMTI|CMTT|CMCSC|CMEX|CMR)", font)
    return m.group(1) if m else "?"


GLYPHS = {"CMR": {11: "ff", 12: "fi", 13: "fl", 14: "ffi", 123: "–", 124: "—"},
          "CMBX": {11: "ff", 12: "fi", 13: "fl", 14: "ffi", 123: "–", 124: "—"},
          "CMMI": {26: "ρ", 58: ".", 59: ",", 60: "<", 62: ">"},
          "CMSY": {0: "−", 2: "×", 102: "{", 103: "}"}}


def page_text(tokens):
    """The page's text with no spaces, ligatures and math codes mapped (rule 1, statements)."""
    out = []
    for text, font in tokens:
        g = GLYPHS.get(family(font), {})
        out.append("".join(g.get(ord(ch), ch) for ch in text))
    return "".join(out).replace(" ", "")


def document(data):
    pdf = Pdf(data)
    pages = pdf.pages()
    if len(pages) != PAGES:
        raise Refused(f"{len(pages)} pages, not {PAGES}")
    return [page_tokens(content, fonts) for content, fonts in pages]


def statements_found(pages, statements=STATEMENTS):
    texts = [page_text(t) for t in pages]
    return {s: any(s.replace(" ", "") in t for t in texts) for s in statements}


# ---------------------------------------------------------------- the tables as tokens (rule 1)

def bold_spec(text, bold):
    return (text, bold)


def table_tokens(name):
    """The table as the PDF's tokens: (text, True if bold, False if not, None if either)."""
    head = [("r", None), ("n", None), ("k", None)] + [(str(k), True) for k in range(3, 10)]
    if name == "table1":
        out = list(head)
        for r, entries in TABLE1.items():
            out.append((str(r), True))
            for value, strict, ref, note in entries:
                if strict:
                    out.append((">", False))
                out += [(str(value), False), ("[", False), (str(ref), False), ("]", False)]
                if note:
                    out.append((note, False))
        return out
    if name == "table4":
        out = list(head)
        for r, entries in TABLE4.items():
            out.append((str(r), True))
            for value, strict, bold in entries:
                if strict:
                    out.append((">", False))
                out.append((str(value), bold))
        return out
    if name == "table3":
        out = [(t, False) for t in ("W", "(", "r", ";", "k", ")", "used", "prime", "zipp", "ed", "result")]
        out += [(t, False) for t in ("W", "(2", ";", "3)", "{", "{", "{")]
        for r, k, p, z, n, bold in TABLE3:
            out += [(t, False) for t in ("W", f"({r}", ";", f"{k})", str(p), str(z), ">")]
            out.append((str(n), bold))
        return out
    if name == "table2":
        out = []
        for q in range(9):
            out += [("q", None), ("=", None), (str(q), None)]
        for i, row in enumerate(TABLE2, 1):
            out += [(t, None) for t in ("C", str(i), ":", "\x1a", "37", f"{i}+4", "q", "(mo", "d", "37)", "+", "1")]
            out += [(str(v), None) for v in row]
        return out
    raise KeyError(name)


def find_table(pages, spec):
    """The one page and place where the spec's texts stand as consecutive tokens, its fonts as specified."""
    want = [t for t, _ in spec]
    hits = []
    for pg, tokens in enumerate(pages, 1):
        texts = [t for t, _ in tokens]
        for i in range(len(texts) - len(want) + 1):
            if texts[i] == want[0] and texts[i:i + len(want)] == want:
                hits.append((pg, i))
    if len(hits) != 1:
        raise Refused(f"a table found {len(hits)} times, not once")
    pg, i = hits[0]
    for (text, bold), (_, font) in zip(spec, pages[pg - 1][i:i + len(want)]):
        if bold is not None and (family(font) == "CMBX") != bold:
            raise Refused(f"{text!r} is in {font}, which is {'not ' if bold else ''}bold against the transcription")
    return pg, i


def read_tables(pages):
    return {name: find_table(pages, table_tokens(name)) for name in ("table1", "table2", "table3", "table4")}


# ---------------------------------------------------------------- the method (rule 2)

def is_prime(m):
    if m < 2:
        return False
    i = 2
    while i * i <= m:
        if m % i == 0:
            return False
        i += 1
    return True


def prime_factors(m):
    out, i = [], 2
    while i * i <= m:
        if m % i == 0:
            out.append(i)
            while m % i == 0:
                m //= i
        i += 1
    if m > 1:
        out.append(m)
    return out


def least_primitive_root(p):
    if not is_prime(p):
        raise Refused(f"{p} is not prime")
    if p == 2:
        return 1
    qs = prime_factors(p - 1)
    for g in range(2, p):
        if all(pow(g, (p - 1) // q, p) != 1 for q in qs):
            return g
    raise Refused(f"no primitive root of {p}")


def full_order(g, p):
    """Whether g's powers run through all p - 1 nonzero residues (by listing them)."""
    seen, x = set(), 1
    for _ in range(p - 1):
        x = x * g % p
        seen.add(x)
    return len(seen) == p - 1


def power_residue(p, r, rho):
    """Rule 2b: the classes 1..r of the numbers 1..p, and which are free (only number 1)."""
    if not is_prime(p) or (p - 1) % r:
        raise Refused(f"p = {p}, r = {r}: the colouring needs a prime p with r dividing p - 1")
    col = [0] * p
    col[0] = 1
    x = 1
    for e in range(1, p):
        x = x * rho % p
        j = x + 1
        if col[j - 1]:
            raise Refused(f"{rho} is not a primitive root of {p}")
        col[j - 1] = (e - 1) % r + 1
    free = [False] * p
    free[0] = True
    return col, free


def point_symmetric_labels(col, r):
    """Rule 2b': the permutation pi (raw class -> label) making the certificate's reverse map C_i onto C_(r+1-i), or
    None if the certificate is not point symmetric. Odd lengths only, number 1 set apart (the paper's j = 2..n)."""
    n = len(col)
    if n % 2 == 0:
        raise Refused("point symmetry is read here for odd lengths only")
    sigma = {}
    for j in range(2, n + 1):
        a, b = col[j - 1], col[n + 2 - j - 1]
        if sigma.setdefault(a, b) != b:
            return None
    if sorted(sigma) != list(range(1, r + 1)):
        return None
    if any(sigma[sigma[c]] != c or sigma[c] == c for c in sigma):
        return None
    pi, label = {}, 1
    for c in range(1, r + 1):
        if c in pi:
            continue
        pi[c], pi[sigma[c]] = label, r + 1 - label
        label += 1
    return pi


def labelled_residue(p, r, rho, pi_labels=True):
    """Rules 2b and 2b': the colouring of 1..p, its free marks, and pi if it was applied."""
    col, free = power_residue(p, r, rho)
    pi = point_symmetric_labels(col, r) if pi_labels else None
    if pi:
        col = [pi[c] for c in col]
    return col, free, pi


def residue_rows(p, r, rho):
    """C_i's entries in the order of q, as Table 2 prints them."""
    return [tuple(pow(rho, i + q * r, p) + 1 for q in range((p - 1) // r)) for i in range(1, r + 1)]


def zip_once(col, free, r, shift):
    """Rule 2c on a certificate of length m: classes and free marks of the zipped certificate of length 2m."""
    m = len(col)
    out, fr = [0] * (2 * m), [False] * (2 * m)
    for j in range(1, m + 1):
        a = 2 * j - 1
        out[a - 1], fr[a - 1] = col[j - 1], free[j - 1]
    for j in range(1, m + 1):
        b = (2 * j - 1 - shift - 1) % (2 * m) + 1
        if out[b - 1]:
            raise Refused(f"zipping: number {b} is taken twice")
        out[b - 1], fr[b - 1] = r + 1 - col[j - 1], free[j - 1]
    if not all(out):
        raise Refused("zipping: the merged classes do not cover 1..2m")
    return out, fr


def build(r, k, p, z, rho, pi_labels=True):
    """Rules 2b to 2d: the text's own certificate of 1..(k - 1) 2^z p + 1 and its free numbers."""
    col, free, _ = labelled_residue(p, r, rho, pi_labels)
    for _ in range(z):
        col, free = zip_once(col, free, r, p)
    N = len(col)
    n = (k - 1) * N + 1
    cert = [col[(y - 1) % N] for y in range(1, n)] + [r]
    fr = [free[(y - 1) % N] for y in range(1, n)] + [True]
    return cert, fr, N


# ---------------------------------------------------------------- the scans (rule 4; C in hhlm.c)

def compile_c(work):
    exe = os.path.join(work, "hhlm")
    subprocess.run(["gcc", "-O3", "-std=gnu11", "-o", exe, os.path.join(HERE, "hhlm.c")], check=True)
    return exe


def write_colouring(path, cert, free=None):
    """Classes 1..r as bytes 0..r-1; free numbers as 255."""
    with open(path, "wb") as fh:
        fh.write(bytes(FREE if free and free[i] else c - 1 for i, c in enumerate(cert)))


def c_scan(exe, path, k):
    out = subprocess.run([exe, "scan", path, str(k)], check=True, capture_output=True, text=True).stdout.split()
    count, pairs, x, d = map(int, out)
    return {"count": count, "pairs": pairs, "first": (x, d) if count else None}


def c_forbid(exe, path, k):
    lines = subprocess.run([exe, "forbid", path, str(k)], check=True, capture_output=True,
                           text=True).stdout.strip().split("\n")
    if not lines or not lines[-1].startswith("multi "):
        raise Refused("forbid: no closing line")
    multi = int(lines[-1].split()[1])
    rows = {}
    for line in lines[:-1]:
        v = list(map(int, line.split()))
        y, mask, wit = v[0], v[1], v[2:]
        rows[y] = {c + 1: (wit[2 * c], wit[2 * c + 1]) for c in range(8) if mask >> c & 1}
    return rows, multi


def py_scan(cert, free, k):
    """A direct enumeration (control): progressions with all numbers fixed and in one class."""
    n, count, pairs = len(cert), 0, 0
    for d in range(1, n):
        for x in range(1, n + 1):
            last = x + (k - 1) * d
            if last > n:
                break
            pairs += 1
            ys = [x + t * d for t in range(k)]
            if not any(free[y - 1] for y in ys) and len({cert[y - 1] for y in ys}) == 1:
                count += 1
    return count, pairs


def py_forbid(cert, free, k):
    n, rows = len(cert), {}
    for y in range(1, n + 1):
        if not free[y - 1]:
            continue
        bad = set()
        for d in range(1, n):
            for t in range(k):
                x = y - t * d
                if x < 1 or x + (k - 1) * d > n:
                    continue
                others = [x + s * d for s in range(k) if s != t]
                if any(free[o - 1] for o in others):
                    continue
                cls = {cert[o - 1] for o in others}
                if len(cls) == 1:
                    bad |= cls
        rows[y] = bad
    return rows


def free_progressions(free_pos, n, k):
    """The k-term progressions of free numbers only."""
    have, out = set(free_pos), []
    for i, a in enumerate(free_pos):
        for b in free_pos[i + 1:]:
            d = b - a
            if a + (k - 1) * d > n:
                break
            ys = tuple(a + t * d for t in range(k))
            if all(y in have for y in ys):
                out.append(ys)
    return out


def search(free_pos, forbidden, own, progs, r):
    """Rule 4 (ii): the first colouring of the free numbers in the search's order, or None; and the nodes visited."""
    idx = {y: i for i, y in enumerate(free_pos)}
    ending = [[] for _ in free_pos]
    for ys in progs:
        ending[idx[ys[-1]]].append([idx[y] for y in ys])
    choices = []
    for i, y in enumerate(free_pos):
        order = [own[i]] + [c for c in range(1, r + 1) if c != own[i]]
        choices.append([c for c in order if c not in forbidden.get(y, set())])
    assign = [0] * len(free_pos)
    nodes = 0

    def ok(i):
        return all(len({assign[j] for j in ys}) > 1 for ys in ending[i])

    def dfs(i):
        nonlocal nodes
        if i == len(free_pos):
            return True
        for c in choices[i]:
            nodes += 1
            if nodes > NODE_LIMIT:
                raise Refused("the search passed its node limit")
            assign[i] = c
            if ok(i) and dfs(i + 1):
                return True
        assign[i] = 0
        return False

    found = dfs(0)
    return (list(assign) if found else None), nodes


def check_row(exe, work, r, k, p, z, n, rho, pi_labels=True):
    """Rule 4 for one row: whether it holds, with everything computed."""
    cert, free, N = build(r, k, p, z, rho, pi_labels)
    pi = labelled_residue(p, r, rho, pi_labels)[2]
    out = {"r": r, "k": k, "p": p, "z": z, "n": n, "rho": rho, "N": N, "built": len(cert),
           "pi": {str(c): v for c, v in pi.items()} if pi else None,
           "length_ok": len(cert) == n == (k - 1) * 2 ** z * p + 1}
    free_pos = [y for y in range(1, len(cert) + 1) if free[y - 1]]
    out["free"] = len(free_pos)
    out["free_as_stated"] = free_pos == [1 + j * p for j in range((k - 1) * 2 ** z + 1)]
    if not out["free_as_stated"]:
        raise Refused(f"W({r},{k}): the free numbers are not the numbers 1 + jp")
    path = os.path.join(work, f"w{r}{k}.bin")
    write_colouring(path, cert, free)
    forbidden, multi = c_forbid(exe, path, k)
    if multi:
        raise Refused(f"W({r},{k}): {multi} progressions hold two free numbers and a fixed one")
    forb = {y: set(w) for y, w in forbidden.items()}
    progs = free_progressions(free_pos, len(cert), k)
    own = [cert[y - 1] for y in free_pos]
    assign, nodes = search(free_pos, forb, own, progs, r)
    out.update({"forbidden": {str(y): sorted(forb[y]) for y in free_pos if forb[y]}, "free_progressions": len(progs),
                "nodes": nodes, "found": assign is not None})
    # the text's own certificate: which of its free numbers' classes break a rule
    own_bad = []
    for i, y in enumerate(free_pos):
        if own[i] in forb[y]:
            x, d = forbidden[y][own[i]]
            own_bad.append({"number": y, "class": own[i], "progression": [x, d]})
    for ys in progs:
        if len({own[free_pos.index(y)] for y in ys}) == 1:
            own_bad.append({"free_progression": list(ys), "class": own[free_pos.index(ys[0])]})
    out["own_breaks"] = own_bad[:5]
    out["own_breaks_count"] = len(own_bad)
    if assign is None:
        fixed = c_scan(exe, path, k)
        out.update({"holds": False, "fixed_scan": fixed, "own_valid": False, "scan": None})
        return out, cert
    final = list(cert)
    for y, c in zip(free_pos, assign):
        final[y - 1] = c
    write_colouring(path, final)
    sc = c_scan(exe, path, k)
    out["scan"] = sc
    out["assignment"] = assign
    out["own_is_first"] = assign == own
    out["own_valid"] = assign == own and sc["count"] == 0
    out["holds"] = out["length_ok"] and sc["count"] == 0
    return out, final


def not_applicable(r, k, p, z, n):
    """Rule 2a: a row whose printed p is not a prime with r dividing p - 1 fails; the method cannot build it."""
    return {"r": r, "k": k, "p": p, "z": z, "n": n, "rho": None, "N": None, "built": 0, "applies": False,
            "length_ok": n == (k - 1) * 2 ** z * p + 1, "free": 0, "found": False, "own_valid": False, "scan": None,
            "holds": False}


# ---------------------------------------------------------------- the table comparisons (rule 5)

def table1_bound(r, k):
    """Table 1's bound on W(r, k) as a lower bound n: W > n."""
    entries = TABLE1.get(r, ())
    if k - 3 >= len(entries) or k < 3:
        return None
    value, strict, _, _ = entries[k - 3]
    return value if strict else value - 1


def improvements():
    return [(r, k, n) for r, k, p, z, n, bold in TABLE3 if table1_bound(r, k) is not None and n > table1_bound(r, k)]


# ---------------------------------------------------------------- seeded streams (controls)

class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m


def random_colouring(st, n, r, free_count):
    cert = [st.below(r) + 1 for _ in range(n)]
    free = [False] * n
    for _ in range(free_count):
        free[st.below(n)] = True
    return cert, free


# ---------------------------------------------------------------- the run

def conditions(rows):
    bold = [(r, k, n) for r, k, p, z, n, b in TABLE3 if b]
    seven = [row for row in rows if (row["r"], row["k"], row["n"]) in set(bold)]
    return {
        "the rows of Table 3 exceeding Table 1's bounds are exactly the seven in bold": (
            len(bold) == 7 and improvements() == bold),
        "each of the seven has n = (k - 1) 2^z p + 1": len(seven) == 7 and all(r["length_ok"] for r in seven),
        "each of the seven certificates, its free numbers coloured, has no k-term progression in one class": (
            len(seven) == 7 and all(r["holds"] for r in seven)),
    }


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    data = read_input(inputs)
    pages = document(data)
    stmts = statements_found(pages)
    places = read_tables(pages)
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)
    try:
        exe = compile_c(work)
        rows, certs = [], {}
        roots = {}
        for r, k, p, z, n, bold in TABLE3:
            if not is_prime(p) or (p - 1) % r:
                row, final = not_applicable(r, k, p, z, n), None
            else:
                rho = least_primitive_root(p)
                roots[p] = rho
                row, final = check_row(exe, work, r, k, p, z, n, rho)
            row["bold"] = bold
            row["table1"] = table1_bound(r, k)
            rows.append(row)
            certs[(r, k)] = final
        cond = conditions(rows)
        # beside: the labels of 2b, no pi (the first program's reading), where pi changes them
        raw = []
        for row in rows:
            pi = row.get("pi")
            if row.get("applies", True) is False or not pi or all(int(c) == v for c, v in pi.items()):
                raw.append({"r": row["r"], "k": row["k"], "bold": row["bold"], "holds": row["holds"],
                            "same_as_pi": True})
                continue
            alt, _ = check_row(exe, work, row["r"], row["k"], row["p"], row["z"], row["n"], row["rho"],
                               pi_labels=False)
            raw.append({"r": row["r"], "k": row["k"], "bold": row["bold"], "holds": alt["holds"], "same_as_pi": False,
                        "scan": alt["scan"], "found": alt["found"]})

        ctl, ctl_detail = {}, {}
        # 1. Table 2
        rho37 = least_primitive_root(37)
        col37, _ = power_residue(37, 4, rho37)
        rows37 = residue_rows(37, 4, rho37)
        ctl["the power residue colouring of 37 over 4 rows with rho = 2 is Table 2"] = (
            rho37 == 2 and tuple(rows37) == TABLE2 and col37[0] == 1
            and all(col37[v - 1] == i for i, row in enumerate(TABLE2, 1) for v in row))
        ctl["its pi interchanges the third and fourth rows and no others"] = (
            point_symmetric_labels(col37, 4) == {1: 1, 2: 2, 3: 4, 4: 3})
        # 2. the C scans against a direct enumeration
        st = Stream(seed, "hhlm/scan")
        agree, cases = 0, []
        for _ in range(SCAN_CONTROLS):
            n = 20 + st.below(71)
            r = 2 + st.below(3)
            k = 3 + st.below(3)
            cert, free = random_colouring(st, n, r, st.below(4))
            path = os.path.join(work, "control.bin")
            write_colouring(path, cert, free)
            sc = c_scan(exe, path, k)
            fb, multi = c_forbid(exe, path, k)
            count, pairs = py_scan(cert, free, k)
            pf = py_forbid(cert, free, k)
            same = (sc["count"] == count and sc["pairs"] == pairs
                    and {y: set(w) for y, w in fb.items()} == pf)
            agree += int(same)
            cases.append({"n": n, "r": r, "k": k, "count": count, "c_count": sc["count"], "multi": multi,
                          "same": same})
        ctl["hhlm.c's scan and forbid agree with a direct enumeration on 30 seed-drawn colourings"] = (
            agree == SCAN_CONTROLS)
        ctl_detail["scan_cases"] = cases
        # 3. a planted progression is found
        st = Stream(seed, "hhlm/plant")
        planted = []
        for r, k in PLANT_IN:
            p, z = next((p, z) for rr, kk, p, z, n, b in TABLE3 if (rr, kk) == (r, k))
            if p not in roots:
                planted.append({"W": [r, k], "count": 0, "first": None, "note": "the construction does not apply"})
                continue
            own, _, _ = build(r, k, p, z, roots[p])
            n = len(own)
            d = 1 + st.below((n - 1) // (k - 1))
            x = 1 + st.below(n - (k - 1) * d)
            for t in range(k):
                own[x + t * d - 1] = own[x - 1]
            path = os.path.join(work, "plant.bin")
            write_colouring(path, own)
            sc = c_scan(exe, path, k)
            planted.append({"W": [r, k], "x": x, "d": d, "count": sc["count"], "first": sc["first"]})
        ctl["a progression planted in the text's certificates for W(2,8), W(4,5) and W(2,9) is found"] = all(
            q["count"] >= 1 for q in planted)
        ctl_detail["planted"] = planted
        # 4. the known values: no extension
        exact = []
        for (r, k), value in EXACT.items():
            row = next(x for x in rows if (x["r"], x["k"]) == (r, k))
            base = certs[(r, k)]
            if base is None:
                exact.append({"W": [r, k], "value": value, "n": 0, "base_holds": False, "extensions_blocked": 0})
                continue
            ext_ok = []
            for c in range(1, r + 1):
                path = os.path.join(work, "extend.bin")
                write_colouring(path, base + [c])
                ext_ok.append(c_scan(exe, path, k)["count"] >= 1)
            exact.append({"W": [r, k], "value": value, "n": len(base), "base_holds": row["holds"],
                          "extensions_blocked": sum(ext_ok)})
        ctl["the certificates for W(2,4), W(2,5), W(4,3) hold and none extends by one number"] = all(
            e["base_holds"] and e["n"] == e["value"] - 1 and e["extensions_blocked"] == e["W"][0] for e in exact)
        ctl_detail["exact"] = exact
        # 5. the search against exhaustion
        st = Stream(seed, "hhlm/search")
        same_search, scases = 0, []
        for _ in range(SEARCH_CONTROLS):
            n = 30 + st.below(31)
            r = 2 + st.below(2)
            k = 3 + st.below(2)
            cert = [st.below(r) + 1 for _ in range(n)]
            qs = [q for q in range(n // 3 + 1, (n - 1) // 2 + 1) if is_prime(q) and q >= k]
            q = qs[st.below(len(qs))]
            free_pos = [1, 1 + q, 1 + 2 * q]
            free = [y in free_pos for y in range(1, n + 1)]
            path = os.path.join(work, "search.bin")
            write_colouring(path, cert, free)
            fb, multi = c_forbid(exe, path, k)
            fixed = c_scan(exe, path, k)["count"]
            progs = free_progressions(free_pos, n, k)
            assign, _ = search(free_pos, {y: set(w) for y, w in fb.items()}, [cert[y - 1] for y in free_pos],
                               progs, r)
            # by exhaustion: a colouring of the free numbers leaving the whole certificate without a progression
            exists = False
            for combo in itertools.product(range(1, r + 1), repeat=len(free_pos)):
                trial = list(cert)
                for y, c in zip(free_pos, combo):
                    trial[y - 1] = c
                if py_scan(trial, [False] * n, k)[0] == 0:
                    exists = True
                    break
            got = assign is not None and fixed == 0 and multi == 0
            if multi:
                got = None
            same_search += int(got == exists)
            scases.append({"n": n, "r": r, "k": k, "q": q, "multi": multi, "search": got,
                           "exhaustion": exists})
        ctl["the search finds a colouring exactly when exhaustion does, on 10 seed-drawn colourings"] = (
            same_search == SEARCH_CONTROLS)
        ctl_detail["search_cases"] = scases
        # 6. primitive roots
        roots_ok = all(full_order(g, p) and not any(full_order(h, p) for h in range(2, g))
                       for p, g in roots.items())
        ctl["for every prime of Table 3, rho's powers run through all p - 1 residues and no smaller number's do"] = (
            roots_ok)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    seven = [x for x in rows if x["bold"]]
    others = [x for x in rows if not x["bold"]]
    def bound4(r, k):
        value, strict, _ = TABLE4[r][k - 3]
        return value if strict else value - 1

    t4 = sum(1 for r, k, p, z, n, b in TABLE3 if bound4(r, k) == n and TABLE4[r][k - 3][2] == b)
    raw_seven = [x for x in raw if x["bold"]]

    def name(x):
        return f"W({x['r']},{x['k']})"

    def listed(prefix, xs):
        """The prefix and the names, as many as fit in LIMIT characters."""
        text = prefix
        for i, x in enumerate(xs):
            more = ("; not in " if i == 0 else ", ") + name(x)
            if len(text) + len(more) + 5 > LIMIT:
                return text + ", ..."
            text += more
        return text

    values = {
        "statements": f"the paper's statements as read: {sum(stmts.values())} of {len(stmts)}",
        "tables": ("Tables 1 to 4 as transcribed, each once: pages "
                   + ", ".join(str(places[t][0]) for t in ("table1", "table2", "table3", "table4"))
                   + "; 7 results bold in Table 3"),
        "improved": "; ".join(f"W({r},{k}) {n} > {table1_bound(r, k)}" for r, k, n in improvements()),
        "lengths": (f"n = (k - 1) 2^z p + 1: {sum(x['length_ok'] for x in seven)} of 7, the other eight "
                    f"{sum(x['length_ok'] for x in others)} of 8"),
        "roots": "least primitive roots: " + ", ".join(f"{x['p']}: {x['rho']}" for x in seven),
        "seven": (f"the seven without a k-term progression in one class: {sum(x['holds'] for x in seven)} of 7"
                  + ("" if all(x["holds"] for x in seven) else "; failing: " + ", ".join(
                      name(x) for x in seven if not x["holds"]))),
        "progressions": sum(x["scan"]["pairs"] for x in seven if x["scan"]),
        "monochromatic": sum(x["scan"]["count"] for x in seven if x["scan"]),
        "free": (f"free numbers in the seven: {sum(x['free'] for x in seven)}; a colouring found for "
                 f"{sum(x['found'] for x in seven)} of 7, the text's own good in {sum(x['own_valid'] for x in seven)}"
                 f" of 7"),
        "text_own": listed(f"the text's own certificates (1 in C1, the added number in Cr) good in "
                           f"{sum(x['own_valid'] for x in rows)} of 15", [x for x in rows if not x["own_valid"]]),
        "others": (f"the other eight rows hold: {sum(x['holds'] for x in others)} of 8"
                   + ("" if all(x["holds"] for x in others) else "; failing: " + ", ".join(
                       name(x) for x in others if not x["holds"]))),
        "raw_reading": listed(f"beside, with the labels of Eq. (1), no pi: the seven hold in "
                              f"{sum(x['holds'] for x in raw_seven)} of 7", [x for x in raw_seven if not x["holds"]]),
        "exact": ("W(2,4) = 35, W(2,5) = 178, W(4,3) = 76: certificates of 34, 177, 75 that hold and do not extend: "
                  + f"{sum(e['base_holds'] and e['extensions_blocked'] == e['W'][0] for e in exact)} of 3"),
        "table4": f"Table 4 for r = 2, 4, 6: {t4} of 15 entries the same bounds as Table 3's, bold alike",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]}, "statements": stmts,
              "tables": {t: list(v) for t, v in places.items()}, "conditions": cond, "controls": ctl,
              "control_detail": ctl_detail, "rows": rows, "raw_reading": raw,
              "roots": {str(p): g for p, g in roots.items()}}
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
        sys.exit(f"hhlm: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
