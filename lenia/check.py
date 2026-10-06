#!/usr/bin/env python3
"""Lenia's species catalogue, counted, and a seeded sample of its species simulated, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:78fcc6363eb1c38c) is from
Chan, "Lenia - Biology of Artificial Life", Complex Systems 28(3) 2019 (arXiv:1812.05433): "More than
400 species in 18 families have been identified, many discovered via interactive evolutionary
computation." Its registered test: refuted if the species catalogue the author released
(Chakazul/Lenia, Python/animals.json at commit 25e107e, January 2020, the first release whose taxonomy
matches the paper's) lists 400 or fewer distinct species or fewer than 18 families; or if more than a
tenth of a seed-chosen sample of 40 of its species, each simulated under its own parameters with the
paper's exponential kernel and growth in a periodic world for t = 30, evaporate (mass below a tenth of
its start) or explode (over half the world filled).

The input is that catalogue (MIT licence, Bert Chan), checked against its SHA-256 and read as data:
a JSON list of header entries (no "cells"; code ">1" to ">4" for class, order, family and subfamily)
and pattern entries (code, name, params {R, T, b, m, s, kn, gn}, cells). The author's simulator,
LeniaND.py at the same commit, was read as the specification; none of its code is used here, and
"LeniaND.py:n" cites its lines. Every choice below was fixed before any seed existed.

1. The count. Walking the list in order, a header at level L becomes the current one at L and clears
   the levels below it. A family is a level-3 header whose name starts with "family:" (so
   "(compilation)" is not one, and the classes SmoothLife and Conway's Game of Life have none). A
   species entry is a pattern entry whose current level-3 header is a family. The species are the
   distinct names among them: the paper defines a species by its morphology and behaviour (section
   3.2.2), and the catalogue gives each such form its own name. Reported beside them: the entries in
   families, their distinct codes and their distinct binomials (a name's first two words, for
   transparency only). The catalogue gives 18 families, 526 entries in them, 433 species, 436 codes
   and 361 binomials.
2. The sample. The species in catalogue order, each represented by its first entry; 40 drawn by a
   partial Fisher-Yates shuffle (for i in 0..39: j = i + below(n - i), swap) with draws from
   ECDYSIS_SEED, SHA-256 in counter mode under the label "lenia/sample" (the Stream of pi/bbp.py), the
   only randomness used. sample_indices lists the drawn entries' places in the catalogue, ascending.
3. One simulation, of one entry under a kernel core, a growth function and a multiplier of mu:
   - the cells decoded as LeniaND's Board.rle2arr and ch2val decode them in two dimensions
     (LeniaND.py:107-112, 168-191), values / 255; a cells string with a delimiter other than "$", a
     character LeniaND's encoder never writes, or no mass is refused;
   - a periodic N x N world, N the smallest power of two at least max(3 max(h, w), 6 R, 128), with
     the pattern's top-left corner at ((N - h) // 2, (N - w) // 2), as LeniaND's Board.add places it;
   - the kernel of the paper's equations 10-12, built as LeniaND.py:312-318 and 408-434 build it:
     D = sqrt(((j - N/2)/R)^2 + ((i - N/2)/R)^2), B = len(beta), K_S = (D < 1) core(min(B D mod 1, 1))
     beta[min(floor(B D), B - 1)], K = K_S / sum(K_S), transformed after np.fft.ifftshift so that its
     centre is at (0, 0);
   - the update of equation 9, A <- clip(A + (1/T) G(real(ifft2(K^ fft2(A)))), 0, 1), for 30 T steps
     (t = 30), in double precision as the paper's section 2.2.4 states, the product K^ fft2(A) taken
     in that order, as LeniaND's calc_once takes it (LeniaND.py:368; see potential below);
   - with M = sum(A) and m0 its start, the entry fails at the first step at which M < m0/10
     (evaporated) or M > N^2/2 (exploded), and the time t = step / T is recorded; otherwise it
     persists, and M(t = 30) / m0 is recorded.
   Cores: exponential exp(4 - 1/(r(1-r))), 0 where r(1-r) = 0; polynomial (4r(1-r))^4; step, 1 on
   [1/4, 3/4]; staircase, the step plus 1/2 on r < 1/4. Growths: exponential 2 exp(-(u-mu)^2/(2s^2)) - 1;
   polynomial 2 max(0, 1 - (u-mu)^2/(9s^2))^4 - 1; step 2 [|u - mu| <= s] - 1.
4. Three variants. "paper": the exponential core and growth for every species (the registered test).
   "code": each entry's own kn and gn mapped as LeniaND.py:272-282, 317 and 370 map them,
   kernel_core[kn - 1] from (polynomial, exponential, step, staircase) and growth_func[gn - 1] from
   (polynomial, exponential, step); so kn = gn = 1, the catalogue's usual values, runs the polynomial
   functions, though LeniaND's own labels (LeniaND.py:2308-2309) call them exponential. "control":
   the paper's functions with mu doubled, which must make the species die.
5. What runs: every species under "paper" and under "code" (the census); the sample's results are read
   from the census; the control on the 40 sampled species. Two worker processes; each simulation
   depends on its entry and variant alone and the results are gathered in a fixed order, so the
   outputs are the same bits serially or pooled, in any order, and nothing reads the clock.

test_passed is 1 if species > 400, families >= 18 and at most 4 of the 40 sampled species fail under
"paper", else 0. control_ok (at least 36 of the 40 die under the control) is reported beside it.

What it cannot check:
- whether the catalogue's names are species in the paper's sense: it counts the names the author gave;
- "many discovered via interactive evolutionary computation": the catalogue does not say how any
  species was found;
- whether a species keeps its form: mass is the only measure, so a pattern that turns into another
  shape of similar mass persists;
- persistence beyond t = 30, or in other worlds, positions or orientations;
- the author's single-precision GPU path (complex64 FFTs); this runs in double precision;
- under "paper", the catalogue's step-function and polynomial species are run with exponential
  functions, as the registered test says; "code" shows each under its own.

Writes results/outputs.json, the 20 outputs the archive accepts for one receipt (strings of at most
200 characters; a longer list is cut to whole items and ends ";+k more"), and results/census.json:
every value computed, uncut (with the sample's codes and each variant's failures), and each species'
fate under each variant with its step count and its mass ratios in full double precision. lenia/README.md
says what each holds, the runtime, and how far the results repeat on other machines.
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, "1")   # one thread in each of the two worker processes

import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import multiprocessing  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from fractions import Fraction  # noqa: E402

import numpy as np  # noqa: E402

INPUT = ("lenia_animals_2020.json", "5544bcf512f4232bc49ead99820443a7952530abb123bf33c8300ec9deae8ba1")
SAMPLE = 40          # species drawn from the seed
HORIZON = 30         # t = 30: 30 T steps of 1/T
MIN_WORLD = 128      # the world is never smaller than 128 x 128
MAX_FAILURES = 4     # more than a tenth of the sample failing refutes the claim
CONTROL_MIN = 36     # the control must kill at least nine in ten
WORKERS = 2
LIMIT = 200          # the archive's longest string output
VARIANTS = ("paper", "code", "control")

# The 20 values results/outputs.json carries (the archive accepts at most 20 per receipt).
OUTPUTS = (
    "catalogue_entries", "families", "family_entries", "species", "species_codes", "species_binomials",
    "sample_size", "sample_indices", "sample_failures", "sample_evaporated", "sample_exploded",
    "sample_failed", "sample_grew_3x", "sample_code_failures", "control_failures", "control_ok",
    "census_paper_failures", "census_code_failures", "steps_simulated", "test_passed",
)


class Stream:
    """As in mm/check.py: SHA-256(seed || "|" || label || "|" || counter), 8 bytes at a time."""

    def __init__(self, seed_hex, label):
        self.seed, self.label, self.counter, self.buf = bytes.fromhex(seed_hex), label.encode("ascii"), 0, b""

    def u64(self):
        if len(self.buf) < 8:
            self.buf += hashlib.sha256(self.seed + b"|" + self.label + b"|" + str(self.counter).encode("ascii")).digest()
            self.counter += 1
        x, self.buf = int.from_bytes(self.buf[:8], "big"), self.buf[8:]
        return x

    def below(self, n):
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            x = self.u64()
            if x < limit:
                return x % n


# ---------------------------------------------------------------- the catalogue, counted

def load(path, sha256):
    """The catalogue as a list of entries, after its bytes are checked against the committed SHA-256."""
    with open(path, "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        sys.exit(f"{path}: sha256 {got}, not the committed {sha256}")
    entries = json.loads(data.decode("utf-8"))
    if not isinstance(entries, list):
        raise ValueError("the catalogue is not a JSON list")
    return entries


def census(entries):
    """The counts, and the catalogue index of each species' first entry, in catalogue order."""
    headers = {}                 # level -> the current header's name
    families = set()
    first = {}                   # species name -> index of its first entry (insertion order = catalogue order)
    codes, binomials = set(), set()
    family_entries = 0
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or not isinstance(e.get("code"), str) or not isinstance(e.get("name"), str):
            raise ValueError(f"entry {i}: not a catalogue entry")
        if "cells" not in e:
            level = re.fullmatch(r">([1-4])", e["code"])
            if level is None:
                raise ValueError(f"entry {i}: a header with code {e['code']!r}")
            level = int(level.group(1))
            headers = {k: v for k, v in headers.items() if k < level}
            headers[level] = e["name"]
            if level == 3 and e["name"].startswith("family:"):
                families.add(e["name"])
            continue
        if not headers.get(3, "").startswith("family:"):
            continue
        family_entries += 1
        first.setdefault(e["name"], i)
        codes.add(e["code"])
        binomials.add(" ".join(e["name"].split()[:2]))
    counts = {
        "catalogue_entries": len(entries),
        "families": len(families),
        "family_entries": family_entries,
        "species": len(first),
        "species_codes": len(codes),
        "species_binomials": len(binomials),
    }
    return counts, list(first.values())


def draw(n, seed, k=SAMPLE):
    """k distinct positions in 0..n-1 by a partial Fisher-Yates shuffle from the seed, in ascending order."""
    stream = Stream(seed, "lenia/sample")
    order = list(range(n))
    for i in range(k):
        j = i + stream.below(n - i)
        order[i], order[j] = order[j], order[i]
    return sorted(order[:k])


# ---------------------------------------------------------------- one pattern, decoded

DIGITS = "0123456789"
PREFIXES = "pqrstuvwxy"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWX"
VALUES = set(".bo" + LETTERS) | {p + c for p in PREFIXES for c in LETTERS}   # what LeniaND's val2ch writes


def ch2val(c):
    """LeniaND.py:107-112: '.' and 'b' are 0, 'o' is 255, A to X are 1 to 24, pA to yO are 25 to 255."""
    if c in ".b":
        return 0
    if c == "o":
        return 255
    if len(c) == 1:
        return ord(c) - ord("A") + 1
    return (ord(c[0]) - ord("p")) * 24 + (ord(c[1]) - ord("A") + 25)


def decode(st):
    """A cells string as LeniaND's Board.rle2arr decodes it in two dimensions (LeniaND.py:168-191), / 255.

    Trailing '!' are dropped and a '$' is appended; a count repeats the value after it, or adds that
    many rows less one (empty) after a '$'; short rows are padded with zeros. Refused: a delimiter of
    more dimensions ('%', '#', '@'), a token LeniaND's encoder never writes, and a pattern with no mass.
    """
    if not isinstance(st, str):
        raise ValueError("cells: not a string")
    body = st.rstrip("!")
    if any(c in "%#@" for c in body):
        raise ValueError("cells: a delimiter other than $ (a pattern of more than two dimensions)")
    rows, row, last, count = [], [], "", ""
    for ch in body + "$":
        if ch in DIGITS:
            count += ch
        elif ch in PREFIXES and not last:
            last = ch
        else:
            token, n = last + ch, int(count) if count else 1
            if token == "$":
                rows.append(row)
                rows.extend([] for _ in range(n - 1))
                row = []
            elif token in VALUES:
                row.extend([ch2val(token) / 255] * max(n, 1))
            else:
                raise ValueError(f"cells: {token!r} is not a value LeniaND writes")
            last, count = "", ""
    width = max(len(r) for r in rows)
    A = np.zeros((len(rows), width))
    for y, r in enumerate(rows):
        A[y, :len(r)] = r
    if not A.sum() > 0:
        raise ValueError("cells: no mass")
    return A


def parameters(params):
    """(R, T, beta, m, s, kn, gn) from an entry's params, checked; beta as floats, as LeniaND.py:198-199 and 315."""
    if not isinstance(params, dict):
        raise ValueError("params: not an object")

    def integer(k, lo, hi):
        v = params.get(k)
        if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
            raise ValueError(f"params.{k}: not an integer from {lo} to {hi}")
        return v

    def real(k):
        v = params.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"params.{k}: not a number")
        return v

    if not isinstance(params.get("b"), str):
        raise ValueError("params.b: not a string of fractions")
    beta = [float(Fraction(f)) for f in params["b"].split(",")]
    s = real("s")
    if not s > 0:
        raise ValueError("params.s: not positive")
    return (integer("R", 1, 10 ** 4), integer("T", 1, 10 ** 5), beta, real("m"), s,
            integer("kn", 1, 4), integer("gn", 1, 3))


def world_size(h, w, R):
    """The smallest power of two at least max(3 max(h, w), 6 R, 128)."""
    need = max(3 * max(h, w), 6 * R, MIN_WORLD)
    return 1 << (need - 1).bit_length()


# ---------------------------------------------------------------- the rule (paper equations 9-13)

def core_polynomial(r):
    return (4 * r * (1 - r)) ** 4


def core_exponential(r):
    """exp(4 - 1/(r(1-r))), 0 where r(1-r) = 0 (LeniaND reaches the same 0 through 1/0 = inf, with a warning)."""
    q = np.asarray(r * (1 - r), dtype=float)
    out = np.zeros_like(q)
    live = q > 0
    with np.errstate(over="ignore"):
        out[live] = np.exp(4 - 1 / q[live])
    return out


def core_step(r):
    return ((r >= 1 / 4) & (r <= 3 / 4)) * 1.0


def core_staircase(r):
    return (r >= 1 / 4) * (r <= 3 / 4) + (r < 1 / 4) * 0.5


def growth_polynomial(u, m, s):
    return np.maximum(0, 1 - (u - m) ** 2 / (9 * s ** 2)) ** 4 * 2 - 1


def growth_exponential(u, m, s):
    return np.exp(-(u - m) ** 2 / (2 * s ** 2)) * 2 - 1


def growth_step(u, m, s):
    return (np.abs(u - m) <= s) * 2 - 1


CORES = {"polynomial": core_polynomial, "exponential": core_exponential, "step": core_step, "staircase": core_staircase}
GROWTHS = {"polynomial": growth_polynomial, "exponential": growth_exponential, "step": growth_step}
CODE_CORES = ("polynomial", "exponential", "step", "staircase")   # LeniaND.py:272-277, kernel_core[kn - 1]
CODE_GROWTHS = ("polynomial", "exponential", "step")              # LeniaND.py:278-282, growth_func[gn - 1]


def functions(kn, gn, m, variant):
    """(core, growth, mu) for a variant."""
    if variant == "paper":
        return "exponential", "exponential", m
    if variant == "code":
        return CODE_CORES[kn - 1], CODE_GROWTHS[gn - 1], m
    if variant == "control":
        return "exponential", "exponential", 2 * m
    raise ValueError(f"no variant {variant!r}")


def kernel(N, R, beta, core):
    """The normalised kernel on the N x N grid, centred at (N/2, N/2), in LeniaND's order of operations."""
    x = (np.arange(N) - N // 2) / R
    D = np.sqrt(x[np.newaxis, :] ** 2 + x[:, np.newaxis] ** 2)
    B = len(beta)
    Br = B * D
    b = np.asarray(beta, dtype=float)[np.minimum(np.floor(Br).astype(int), B - 1)]
    K = (D < 1) * CORES[core](np.minimum(Br % 1, 1)) * b
    total = K.sum()
    if not total > 0:
        raise ValueError("the kernel is empty")
    return K / total


def kernel_fft(N, R, beta, core):
    return np.fft.fft2(np.fft.ifftshift(kernel(N, R, beta, core)))


def potential(Khat, A):
    """U = K * A on the torus (paper equation 7), by FFT, the product taken as np.multiply(Khat, fft2(A)).

    Not `Khat * np.fft.fft2(A)`: numpy's complex multiply fuses one of its two products (fmaddsub), so the
    imaginary parts of K F and F K can differ in the last bit, and numpy's temporary elision turns
    `Khat * <a fresh array of 256 KiB or more>` into `F *= Khat` (F K) under some interpreters (Python 3.12,
    as in the pinned image) and not others (3.13). A ufunc called by name is never elided, so the order is
    always K F, as in LeniaND's calc_once (LeniaND.py:368).
    """
    return np.real(np.fft.ifft2(np.multiply(Khat, np.fft.fft2(A))))


def setup(cells, params, variant):
    """The start of a run: (A, Khat, G, mu, s, T), A the pattern placed in its N x N world."""
    A0 = decode(cells)
    R, T, beta, m, s, kn, gn = parameters(params)
    core, growth, mu = functions(kn, gn, m, variant)
    h, w = A0.shape
    N = world_size(h, w, R)
    A = np.zeros((N, N))
    A[(N - h) // 2:(N - h) // 2 + h, (N - w) // 2:(N - w) // 2 + w] = A0
    return A, kernel_fft(N, R, beta, core), GROWTHS[growth], mu, s, T


def step(A, Khat, G, mu, s, dt):
    """One update (paper equation 9), in LeniaND's order of operations (LeniaND.py:364-393)."""
    return np.clip(A + dt * G(potential(Khat, A), mu, s), 0, 1)


def simulate(cells, params, variant):
    """One entry under one variant, to t = 30 or its first failure.

    Returns (fate, steps, t, mass, low, high, N, m0): fate is "persists", "evaporated" or "exploded";
    steps the updates made; t = steps / T; mass, low and high the last, least and greatest M / m0.
    """
    A, Khat, G, mu, s, T = setup(cells, params, variant)
    N = A.shape[0]
    dt = 1 / T
    m0 = A.sum()
    ratio = low = high = 1.0
    for k in range(1, HORIZON * T + 1):
        A = step(A, Khat, G, mu, s, dt)
        M = A.sum()
        if not math.isfinite(M):
            raise FloatingPointError("the mass is not finite")
        ratio = M / m0
        low, high = min(low, ratio), max(high, ratio)
        if M < m0 / 10:
            return ("evaporated", k, k / T, ratio, low, high, N, m0)
        if M > N * N / 2:
            return ("exploded", k, k / T, ratio, low, high, N, m0)
    return ("persists", HORIZON * T, float(HORIZON), ratio, low, high, N, m0)


# ---------------------------------------------------------------- the run

def run_one(job):
    cells, params, variant = job
    return simulate(cells, params, variant)


def cost(job):
    """A rough count of the work in a job, for scheduling only: steps times N^2 log N."""
    cells, params, _ = job
    h, w = decode(cells).shape
    N = world_size(h, w, params["R"])
    return HORIZON * params["T"] * N * N * N.bit_length()


def run_all(jobs):
    """Every job's result, in the order of jobs. The costliest start first, on two workers."""
    order = sorted(range(len(jobs)), key=lambda k: (-cost(jobs[k]), k))
    queue = [jobs[k] for k in order]
    pool = None
    try:
        pool = multiprocessing.get_context("fork").Pool(WORKERS)
        done = pool.imap(run_one, queue, chunksize=1)
    except (OSError, ValueError, ImportError) as e:   # no fork, or no shared memory for the pool's locks
        print(f"lenia/check.py: no worker pool ({e}); running serially", file=sys.stderr)
        done = map(run_one, queue)
    results = [None] * len(jobs)
    try:
        for n, (k, r) in enumerate(zip(order, done), start=1):
            results[k] = r
            if n % 100 == 0 or n == len(jobs):
                print(f"lenia/check.py: {n} of {len(jobs)} simulations", file=sys.stderr)
    finally:
        if pool is not None:
            pool.terminate()
            pool.join()
    return results


def bounded(items, limit=LIMIT):
    """items joined by ';', cut to whole items ending ';+k more' when longer than limit characters."""
    text = ";".join(items)
    k = len(items)
    while len(text) > limit:
        k -= 1
        text = ";".join(items[:k] + [f"+{len(items) - k} more"])
    return text


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    entries = load(os.path.join("inputs", INPUT[0]), INPUT[1])
    counts, species = census(entries)
    if len(species) < SAMPLE:
        sys.exit(f"{len(species)} species, fewer than the sample of {SAMPLE}")
    for i in species:
        try:
            decode(entries[i]["cells"])
            parameters(entries[i].get("params"))
        except ValueError as e:
            sys.exit(f"entry {i} ({entries[i]['code']}): {e}")
    sampled = [species[j] for j in draw(len(species), seed)]

    tasks = [(i, v) for i in species for v in ("paper", "code")] + [(i, "control") for i in sampled]
    results = run_all([(entries[i]["cells"], entries[i]["params"], v) for i, v in tasks])
    fate = dict(zip(tasks, results))

    def tally(ids, variant):
        rs = [(i, fate[(i, variant)]) for i in ids]
        failed = [(i, r) for i, r in rs if r[0] != "persists"]
        return {
            "failures": len(failed),
            "evaporated": sum(1 for _, r in failed if r[0] == "evaporated"),
            "exploded": sum(1 for _, r in failed if r[0] == "exploded"),
            "grew_3x": sum(1 for _, r in rs if r[0] == "persists" and r[3] > 3),
            "failed": [f"{entries[i]['code']}:{r[0]}@{r[2]:.1f}" for i, r in failed],
        }

    paper, code = tally(species, "paper"), tally(species, "code")
    sp, sc, ctl = tally(sampled, "paper"), tally(sampled, "code"), tally(sampled, "control")
    values = dict(counts)
    values.update({
        "sample_size": len(sampled),
        "sample_codes": ",".join(entries[i]["code"] for i in sampled),
        "sample_indices": ",".join(str(i) for i in sampled),
        "sample_failures": sp["failures"],
        "sample_evaporated": sp["evaporated"],
        "sample_exploded": sp["exploded"],
        "sample_failed": ";".join(sp["failed"]),
        "sample_grew_3x": sp["grew_3x"],
        "sample_code_failures": sc["failures"],
        "control_failures": ctl["failures"],
        "control_ok": 1 if ctl["failures"] >= CONTROL_MIN else 0,
        "census_species": len(species),
        "steps_simulated": sum(r[1] for r in results),
    })
    for name, t in (("paper", paper), ("code", code)):
        for k in ("failures", "evaporated", "exploded", "grew_3x"):
            values[f"census_{name}_{k}"] = t[k]
        values[f"census_{name}_failed"] = ";".join(t["failed"])
    values["test_passed"] = 1 if (counts["species"] > 400 and counts["families"] >= 18
                                  and sp["failures"] <= MAX_FAILURES) else 0

    out = {k: values[k] for k in OUTPUTS}
    out["sample_failed"] = bounded(sp["failed"])
    picked = set(sampled)
    record = []
    for i in species:
        paper_run = fate[(i, "paper")]
        row = {"index": i, "code": entries[i]["code"], "name": entries[i]["name"], "sampled": i in picked,
               "N": paper_run[6], "m0": float(paper_run[7]), "fates": {}}
        for v in VARIANTS:
            r = fate.get((i, v))
            if r is not None:   # floats in full: json writes the shortest repr that reads back to the same double
                row["fates"][v] = {"fate": r[0], "steps": r[1], "t": float(r[2]), "mass": float(r[3]),
                                   "low": float(r[4]), "high": float(r[5])}
        record.append(row)

    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join("results", "census.json"), "w", encoding="ascii") as f:
        json.dump({"values": values, "species": record}, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
