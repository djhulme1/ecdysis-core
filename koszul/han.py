#!/usr/bin/env python3
"""Han's border Waring rank of x1...xn: the Young flattening of the proof, computed for n = 2 to 7, for an Ecdysis
receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:88445feacc817241) is from Jong In Han, "The
border Waring rank of $x_1\\cdots x_n$ is $2^{n-1}$" (arXiv:2609.09141v1, 2026): "In this paper, we show that the border
Waring rank of $x_1x_2\\cdots x_n$ over fields of characteristic zero is exactly $2^{n-1}$."

Its registered test: refuted if, for some n from 2 to 7, the Young flattening F_{lambda,lambda~}(x1...xn) of the proof
(lambda = (n-1, ..., 1), lambda~ = (n, ..., 1)), computed as the higher-order Koszul flattening of the n x n permanent
tensor with p = (0, 1, ..., n-1) followed by the projection onto S_lambda~ V, has rank below 2^C(n,2) at seed-drawn
points modulo each of two primes near 2^31, or the same for x1^n has rank above 2^C(n-1,2); or the polarization identity
x1...xn = (2^(n-1) n!)^(-1) sum_{delta_1 = 1} (prod delta_k)(sum delta_j x_j)^n fails for some n from 2 to 8.

The input is the paper's v1 e-print from arXiv, checked against its SHA-256 and read as data (the tar opened with the
standard library and its TeX read as text; nothing in it is run). Every rule below was fixed before any rank was
computed. The seed draws the evaluation points; it does not touch what is computed.

1. The source. With its TeX comments removed and its whitespace collapsed, bwrk_sqfree.tex must hold each formula and
   statement in PRINTED_TEX (the theorem, the shapes, the Koszul and Young flattening bounds, the two ranks, the
   identity, the parity step, the previous bounds' table); otherwise the run is refused.
2. The spaces. Letters 0..n-1 stand for e_1..e_n. W_lambda = wedge^(n-1) V (x) ... (x) wedge^1 V has the basis of tuples
   of increasing columns of lengths n-1, ..., 1 (the staircase's columns); W_lambda~ has one more column, of length n,
   in front. The higher-order Koszul flattening (the paper's Theorem 2.3, with p = (0, 1, ..., n-1)) of a tensor term
   e_{i_0} (x) ... (x) e_{i_(n-1)} sends a tuple to the tuple whose column of length k gets e_{i_k} wedged in front
   (e_i wedge c = (-1)^#{x in c : x < i} times the sorted column; zero if i is in c), the empty column receiving i_0.
   Its first column is then the full set and is struck off (the paper's Phi^-1), leaving a tuple of W_lambda's shape.
   The permanent tensor is the sum of its n! permutation terms; the determinant's carries the sign of the permutation;
   x1^n is the single term (0, ..., 0); x1^(n-1) x2 the n arrangements of one 1 among 0s.
3. The projection. A tuple maps to the product, over its columns c, of the minor of a generic n x (n-1) matrix X on rows
   c and columns 0..|c|-1 (a bideterminant). This map is GL(V)-equivariant with image S_lambda V, in which the
   semistandard tableaux give a basis (the straightening theorem), and it kills the other components of W_lambda; and
   for a symmetric (or alternating) tensor the flattening composed with it kills every component of W_lambda but
   S_lambda (Pieri: lambda~ minus a horizontal, or vertical, strip of n boxes is only lambda). So the rank of the Young
   flattening equals the dimension of the span of the projected images of the semistandard tableaux.
4. The rank. The flattening keeps torus weight (shifted by the tensor's weight), so it is computed block by block over
   the contents nu of the source tableaux, one representative per orbit of the permutations of letters that fix the
   tensor (the S_n symmetry for the permanent), weighted by the orbit's size. In each block, the images of the K
   semistandard tableaux of content nu are evaluated at K + EXTRA points X drawn from the seed (SHA-256 of seed, prime,
   n and position, modulo the prime), and the rank of that K x (K + EXTRA) matrix is found by Gaussian elimination
   modulo PRIMES[0]; where it falls short, again at fresh points modulo PRIMES[1]. Evaluation can only lower a rank, so
   a rank found is a lower bound on the true one, and K (the Kostka number) is an upper bound.
5. The test's three conditions. (1) For every n from 2 to 7, the rank for x1...xn is 2^C(n,2) (it fails only if some
   block falls short modulo both primes). (2) For every n from 2 to 7, the rank for x1^n is at most 2^C(n-1,2): the
   weights it can reach (those with n-1 letters 0, its tensor's weight being (n, 0, ..., 0)) have Kostka numbers summing
   to 2^C(n-1,2), which bounds it, and the rank found must not exceed that (it fails if it does). (3) The identity,
   expanded exactly by the multinomial theorem over the 2^(n-1) sign vectors, equals x1...xn for n = 2 to 8.
   test_passed is 1 if all three hold.
6. Beside the test: the bound 2^C(n,2)/2^C(n-1,2) = 2^(n-1) against the paper's table of previous bounds; and, for
   n = 2 to 6, the ranks of the unprojected Koszul flattenings of the permanent and determinant tensors on W_lambda
   (the paper: the determinant's is full, the permanent's "need not" be).
7. Controls: both primes pass Miller-Rabin; for n = 2 to 7 the orbit-weighted Kostka numbers sum to 2^C(n,2), the
   dimension of S_lambda V by the Weyl formula; for n = 2 to 6 the semistandard tableaux of every block evaluate to K
   independent vectors (the projection is the Schur module); Psi(det_n) is a scalar multiple of the identity on every
   block (the paper's use of Schur's lemma), for n = 2 to 6; the two implementations of the flattening (the
   permutation recursion and the term list) agree for n = 2 to 5; and, as a negative control, x1^(n-1) x2, of border
   rank 2, has rank at most twice that of x1^n for n = 2 to 6.

What it cannot check: Theorem A for n above 7, or the parity argument itself; only the flattening's ranks, which the
proof turns into the bound, for n up to 7.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 koszul/han.py
"""

import functools
import hashlib
import io
import itertools
import json
import math
import os
import re
import sys
import tarfile
from collections import Counter

import numpy as np
import scipy.sparse as sp

INPUTS = {"eprint": ("arXiv-2609.09141v1.tar.gz", "5e6cbefa969668852ac9a91a8ca1aa70565c21984292a9a7c5419895691009f3")}
TEX = "bwrk_sqfree.tex"
PRINTED_TEX = (
    r"In this paper, we show that the border Waring rank of $x_1x_2\cdots x_n$ over fields of characteristic zero is "
    r"exactly $2^{n-1}$.",
    r"x_1x_2\cdots x_n=\frac{1}{2^{n-1}n!}\sum_{\substack{(\delta_1,\ldots,\delta_n)\in\{1,-1\}^{n}\\ \delta_1=1}}"
    r"\left(\prod_{k=1}^n\delta_k\right)\left(\sum_{j=1}^n\delta_j x_j\right)^n",
    r"lower bound & $4$ & $8$ & $16$ & $29$ & $55$ & $71$ & $138$ & $253$ & $498$ & $\cdots$",
    r"\bwrk(f)\ge \dfrac{\rank\mathcal{F}_{\ld,\mu}(f)}{\rank\mathcal{F}_{\ld,\mu}(x_1^d)}.",
    r"\brk(T)\ge \frac{\rank\left(T^{\wedge(p_1,\dots,p_n)}_{(V_1,\dots,V_n)}\right)}{\binom{d_1-1}{p_1}\cdots"
    r"\binom{d_n-1}{p_n}}.",
    r"It holds that $\bwrk(x_1x_2\cdots x_n)=2^{n-1}$ over fields of characteristic zero.",
    r"We pick the partitions $\ld=(n-1,n-2,\dots,1)$, $\lt=(n,n-1,\dots,1)$, and regard these as Young diagrams.",
    r"The higher-order Koszul flattening of the $n\times n$ determinant tensor $\det_n$ with "
    r"$(p_1,p_2,\dots,p_n)=(0,1,\dots,n-1)$ is",
    r"\dim \s_\ld V=\prod_{1\le i<j\le n}\frac{\ld_i-\ld_j+j-i}{j-i}=2^{\binom{n}{2}}.",
    r"Note that $\per_n\equiv \det_n$ modulo 2.",
    r"\rank\mathcal{F}_{\ld,{\lt}}(\per_n)=\dim \s_\ld V=2^{\binom{n}{2}}.",
    r"Now we show that $\rank\mathcal{F}_{\ld,{\lt}}(x_1^n)\le 2^{\binom{n-1}{2}}$.",
    r"\bwrk(\per_n)\ge \frac{\rank\mathcal{F}_{\ld,{\lt}}(\per_n)}{\rank\mathcal{F}_{\ld,{\lt}}(x_1^n)}\ge "
    r"\frac{2^{\binom{n}{2}}}{2^{\binom{n-1}{2}}}=2^{n-1}",
)
N_TEST = tuple(range(2, 8))
N_SMALL = tuple(range(2, 7))
N_AGREE = tuple(range(2, 6))
N_POLAR = tuple(range(2, 9))
PRIMES = (2147483647, 2147483629)
EXTRA = 16
CHUNK = 128
PREVIOUS = {3: 4, 4: 8, 5: 16, 6: 29, 7: 55}            # the paper's table: the best lower bounds before it
OUTPUTS = ("source", "per_ranks", "power_ranks", "power_reach", "bounds", "polarization", "det_scalars",
           "twin_ranks", "raw_ranks", "blocks", "basis", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# --- reading -----------------------------------------------------------------------------------------------------

def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


def tex_of(eprint):
    try:
        with tarfile.open(fileobj=io.BytesIO(eprint), mode="r:gz") as t:
            member = t.getmember(TEX)
            return t.extractfile(member).read().decode("utf-8")
    except KeyError:
        raise Refused(f"the e-print holds no {TEX}") from None
    except (tarfile.TarError, OSError, EOFError) as e:
        raise Refused(f"the e-print is not a gzipped tar: {e}") from None


def flatten(tex):
    """TeX comments removed (an unescaped % to the end of its line), then whitespace collapsed."""
    lines = [re.sub(r"(?<!\\)%.*$", "", line) for line in tex.split("\n")]
    return re.sub(r"\s+", " ", " ".join(lines))


def check_source(tex):
    flat = flatten(tex)
    for s in PRINTED_TEX:
        if s not in flat:
            raise Refused(f"the e-print does not hold, as read: {s[:80]!r}")


# --- tableaux --------------------------------------------------------------------------------------------------------

def staircase(n):
    return tuple(range(n - 1, 0, -1))


def strips_removed(shape, k):
    """The shapes mu with shape/mu a horizontal strip of k boxes (shape[i+1] <= mu[i] <= shape[i])."""
    out = []

    def rec(i, mu, left):
        if i == len(shape):
            if left == 0:
                out.append(tuple(x for x in mu if x > 0))
            return
        lo = shape[i + 1] if i + 1 < len(shape) else 0
        for r in range(0, min(shape[i] - lo, left) + 1):
            rec(i + 1, mu + [shape[i] - r], left - r)
    rec(0, [], k)
    return out


@functools.lru_cache(maxsize=None)
def kostka(shape, content):
    """The number of semistandard tableaux of the shape with the content (multiplicities of letters 0, 1, ...)."""
    if not content:
        return 1 if sum(shape) == 0 else 0
    return sum(kostka(mu, content[:-1]) for mu in strips_removed(shape, content[-1]))


def columns_of(rows):
    width = len(rows[0]) if rows else 0
    return tuple(tuple(r[c] for r in rows if len(r) > c) for c in range(width))


def ssyt(shape, content):
    """Every semistandard tableau of the shape with the content, as its tuple of columns (each increasing)."""
    out = []

    def add(letter, rows):
        if letter == len(content):
            if all(len(r) == s for r, s in zip(rows, shape)):
                out.append(columns_of(rows))
            return

        def rec(i, left, new_rows):
            if i == len(shape):
                if left == 0:
                    add(letter + 1, new_rows)
                return
            cur = len(rows[i])
            cap = shape[i] if i == 0 else min(shape[i], len(rows[i - 1]))
            for r in range(0, min(cap - cur, left) + 1):
                rec(i + 1, left - r, new_rows + [rows[i] + [letter] * r])
        rec(0, content[letter], [])
    add(0, [[] for _ in shape])
    return out


def weyl_dimension(shape, n):
    lam = list(shape) + [0] * (n - len(shape))
    num = den = 1
    for i in range(n):
        for j in range(i + 1, n):
            num *= lam[i] - lam[j] + j - i
            den *= j - i
    return num // den


def class_contents(classes, total, maxpart):
    """Contents (one entry per letter) summing to total, entries at most maxpart, non-increasing within each class of
    letters; with the size of each one's orbit under the permutations within classes."""
    n = sum(len(c) for c in classes)
    found = []

    def seqs(m, budget, top):
        if m == 0:
            yield ()
            return
        for a in range(min(top, budget), -1, -1):
            for rest in seqs(m - 1, budget - a, a):
                yield (a,) + rest

    def rec(ci, budget, assign):
        if ci == len(classes):
            if budget == 0:
                nu = [0] * n
                orbit = 1
                for cls, vals in zip(classes, assign):
                    for idx, v in zip(cls, vals):
                        nu[idx] = v
                    mult = Counter(vals)
                    orbit *= math.factorial(len(cls)) // math.prod(math.factorial(x) for x in mult.values())
                found.append((tuple(nu), orbit))
            return
        for vals in seqs(len(classes[ci]), budget, maxpart):
            rec(ci + 1, budget - sum(vals), assign + [vals])
    rec(0, total, [])
    return found


# --- the flattening ------------------------------------------------------------------------------------------------
# Columns are bitmasks of letters; a tuple of n-1 columns is packed into one integer, column c in bits n*c .. n*c+n-1.

def to_masks(cols):
    return tuple(sum(1 << x for x in col) for col in cols)


def pack(masks, n):
    key = 0
    for c, m in enumerate(masks):
        key |= m << (n * c)
    return key


def unpack(key, n, ncols):
    full = (1 << n) - 1
    return tuple((key >> (n * c)) & full for c in range(ncols))


def wedge_front(i, mask):
    """e_i wedge the column: (sign, new mask), or None if i is in the column."""
    if mask >> i & 1:
        return None
    return (-1) ** (mask & ((1 << i) - 1)).bit_count(), mask | (1 << i)


def perm_sign(perm):
    s = 1
    for a in range(len(perm)):
        for b in range(a + 1, len(perm)):
            if perm[a] > perm[b]:
                s = -s
    return s


def image_perm(t, n, signed):
    """The permanent tensor (signed=False) or the determinant tensor (signed=True) through the Koszul flattening, its
    first column struck off: {packed tuple: coefficient}. t is a tuple of n-1 column masks (lengths n-1, ..., 1).
    Column c (the empty column is c = n-1) receives the letter of factor n-1-c; factors are filled from n-1 down, so
    each new letter's inversions with the factors already filled are the used letters below it."""
    full = (1 << n) - 1
    rest = full & ~t[0]
    if rest.bit_count() != 1:
        raise ValueError("the first column must miss exactly one letter")
    m = rest.bit_length() - 1
    s0 = (-1) ** (t[0] & ((1 << m) - 1)).bit_count()
    cols = list(t[1:]) + [0]
    out = {}

    def rec(c, sign, used, key):
        if c == n:
            out[key] = out.get(key, 0) + sign
            return
        col = cols[c - 1]
        free = full & ~used & ~col
        while free:
            low = free & -free
            free ^= low
            w = (-1) ** (col & (low - 1)).bit_count()
            if signed:
                w *= (-1) ** (used & (low - 1)).bit_count()
            rec(c + 1, sign * w, used | low, key | ((col | low) << (n * (c - 1))))
    rec(1, s0, 1 << m, 0)
    return {k: v for k, v in out.items() if v}


def image_terms(t, n, terms):
    """A tensor given as [(coefficient, (i_0, ..., i_(n-1)))] through the Koszul flattening, first column struck off."""
    cols = list(t) + [0]
    out = {}
    for coef, idx in terms:
        sign = coef
        newcols = []
        for c in range(n):
            w = wedge_front(idx[n - 1 - c], cols[c])
            if w is None:
                break
            sign *= w[0]
            newcols.append(w[1])
        else:
            key = pack(newcols[1:], n)
            out[key] = out.get(key, 0) + sign
    return {k: v for k, v in out.items() if v}


def perm_terms(n, signed):
    return [(perm_sign(p) if signed else 1, p) for p in itertools.permutations(range(n))]


def power_terms(n):
    return [(1, (0,) * n)]


def twin_terms(n):
    return [(1, tuple(1 if k == j else 0 for k in range(n))) for j in range(n)]


# --- evaluation ------------------------------------------------------------------------------------------------------

def draw_points(seed, prime, n, count):
    """count matrices n x (n-1) modulo the prime, each entry from SHA-256 of the seed, prime, n and its position."""
    X = np.zeros((count, n, n - 1), dtype=np.int64)
    for j in range(count):
        for r in range(n):
            for c in range(n - 1):
                h = hashlib.sha256(f"{seed}|{prime}|{n}|{j}|{r}|{c}".encode()).digest()
                X[j, r, c] = int.from_bytes(h[:8], "big") % prime
    return X


def minors_table(X, p):
    """M[mask] = the minor of each X on the rows in mask (in order) and its first |mask| columns; M[0] = 1."""
    count, n, _ = X.shape
    M = np.zeros((1 << n, count), dtype=np.int64)
    M[0] = 1
    for mask in sorted(range(1, 1 << n), key=lambda m: bin(m).count("1")):
        k = bin(mask).count("1")
        if k > n - 1:
            continue
        rows = [i for i in range(n) if mask >> i & 1]
        acc = np.zeros(count, dtype=np.int64)
        for pos, r in enumerate(rows):
            term = (X[:, r, k - 1] * M[mask & ~(1 << r)]) % p
            acc = (acc - term) % p if (pos + k - 1) % 2 else (acc + term) % p
        M[mask] = acc
    return M


def evaluate(images, n, M, npoints, p):
    """The values of each image (a dict tuple -> coefficient) at the first npoints points: a len(images) x npoints
    array modulo p."""
    index = {}
    rows, cols, vals = [], [], []
    for k, img in enumerate(images):
        for tup, coef in img.items():
            u = index.setdefault(tup, len(index))
            rows.append(k)
            cols.append(u)
            vals.append(coef)
    out = np.zeros((len(images), npoints), dtype=np.int64)
    if not index:
        return out
    keys = np.array(list(index), dtype=np.int64)
    masks = np.stack([(keys >> (n * c)) & ((1 << n) - 1) for c in range(n - 1)], axis=1)
    A = sp.csr_matrix((np.array(vals, dtype=np.int64), (np.array(rows), np.array(cols))),
                      shape=(len(images), len(index)), dtype=np.int64)
    for a in range(0, npoints, CHUNK):
        b = min(npoints, a + CHUNK)
        Msl = M[:, a:b]
        E = np.ones((len(index), b - a), dtype=np.int64)
        for c in range(masks.shape[1]):
            E = (E * Msl[masks[:, c]]) % p
        out[:, a:b] = np.asarray(A @ E) % p
    return out


def rank_mod(mat, p):
    """The rank of an integer matrix modulo the prime p (Gaussian elimination; entries below 2^31)."""
    A = np.array(mat, dtype=np.int64) % p
    nr, nc = A.shape
    r = 0
    for c in range(nc):
        if r == nr:
            break
        nz = np.flatnonzero(A[r:, c])
        if nz.size == 0:
            continue
        piv = r + int(nz[0])
        if piv != r:
            A[[r, piv]] = A[[piv, r]]
        inv = pow(int(A[r, c]), p - 2, p)
        A[r, c:] = (A[r, c:] * inv) % p
        below = r + 1 + np.flatnonzero(A[r + 1:, c])
        if below.size:
            f = A[below, c][:, None]
            A[below, c:] = (A[below, c:] - (f * A[r, c:]) % p) % p
        r += 1
    return r


def is_prime(m):
    if m < 2:
        return False
    for q in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if m % q == 0:
            return m == q
    d, s = m - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, m)
        if x in (1, m - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, m)
            if x == m - 1:
                break
        else:
            return False
    return True


class Points:
    """The seed's evaluation points and their minors, per (n, prime), drawn as far as needed."""

    def __init__(self, seed):
        self.seed = seed
        self.tables = {}

    def table(self, n, pi, count):
        key = (n, pi)
        have = self.tables.get(key)
        if have is None or have.shape[1] < count:
            p = PRIMES[pi]
            self.tables[key] = minors_table(draw_points(self.seed, p, n, count), p)
        return self.tables[key]


def flattening_rank(n, image_of, classes, points):
    """The rank of the Young flattening of one tensor: per block of source content (one per orbit), the evaluation rank
    of the images of its semistandard tableaux, the first prime and then the second where the first falls short.
    Returns (rank, blocks), blocks a list of dicts."""
    lam = staircase(n)
    blocks = []
    found = [(nu, orbit) for nu, orbit in class_contents(classes, sum(lam), n - 1)
             if kostka(lam, tuple(sorted(nu, reverse=True))) > 0]
    srcs = {nu: [to_masks(t) for t in ssyt(lam, nu)] for nu, _ in found}
    need = max((len(s) for s in srcs.values()), default=0) + EXTRA
    total = 0
    for nu, orbit in found:
        tabs = srcs[nu]
        imgs = [image_of(t) for t in tabs]
        if not any(imgs):
            blocks.append({"content": nu, "orbit": orbit, "K": len(tabs), "rank": 0, "prime": None})
            continue
        K = len(tabs)
        rank, used = 0, None
        for pi in range(len(PRIMES)):
            M = points.table(n, pi, need)
            r = rank_mod(evaluate(imgs, n, M, K + EXTRA, PRIMES[pi]), PRIMES[pi])
            if r > rank:
                rank, used = r, pi
            if rank == K:
                break
        blocks.append({"content": nu, "orbit": orbit, "K": K, "rank": rank, "prime": used})
        total += orbit * rank
    return total, blocks


# --- the identity --------------------------------------------------------------------------------------------------

def compositions(total, parts):
    if parts == 1:
        yield (total,)
        return
    for a in range(total, -1, -1):
        for rest in compositions(total - a, parts - 1):
            yield (a,) + rest


def polarization_holds(n):
    """sum over delta in {1,-1}^n with delta_1 = 1 of (prod delta)(sum delta_j x_j)^n, expanded exactly, is
    2^(n-1) n! x1...xn."""
    alphas = [(a, math.factorial(n) // math.prod(math.factorial(x) for x in a)) for a in compositions(n, n)]
    acc = Counter()
    for signs in itertools.product((1, -1), repeat=n - 1):
        d = (1,) + signs
        pd = math.prod(d)
        for a, mult in alphas:
            acc[a] += pd * mult * math.prod(dj ** aj for dj, aj in zip(d, a))
    got = {k: v for k, v in acc.items() if v}
    return got == {(1,) * n: 2 ** (n - 1) * math.factorial(n)}


# --- controls and beside --------------------------------------------------------------------------------------------

def basis_independent(n, points):
    """Every block's semistandard tableaux, projected, are independent at the points (modulo the first prime)."""
    lam = staircase(n)
    ok = True
    for nu, _ in class_contents([list(range(n))], sum(lam), n - 1):
        tabs = [to_masks(t) for t in ssyt(lam, nu)]
        if not tabs:
            continue
        K = len(tabs)
        M = points.table(n, 0, K + EXTRA)
        ok = ok and rank_mod(evaluate([{pack(t, n): 1} for t in tabs], n, M, K + EXTRA, PRIMES[0]), PRIMES[0]) == K
    return ok


def det_scalar(n, points, npts=8):
    """Psi(det_n) against the identity on every block, at npts points modulo the first prime: the one scalar c with
    Psi(det_n)(t) = c t for every tableau t, or None if there is none."""
    lam = staircase(n)
    p = PRIMES[0]
    M = points.table(n, 0, npts)
    c = None
    for nu, _ in class_contents([list(range(n))], sum(lam), n - 1):
        tabs = [to_masks(t) for t in ssyt(lam, nu)]
        if not tabs:
            continue
        got = evaluate([image_perm(t, n, True) for t in tabs], n, M, npts, p)
        own = evaluate([{pack(t, n): 1} for t in tabs], n, M, npts, p)
        if c is None:
            r, j = (int(x[0]) for x in np.nonzero(own))
            c = int(got[r, j]) * pow(int(own[r, j]), p - 2, p) % p
        if not np.array_equal(got, (own * c) % p):
            return None
    return c if c <= p // 2 else c - p


def w_tuples(n, content):
    """Every tuple of W_lambda's shape with the given content."""
    lengths = staircase(n)
    out = []

    def rec(j, left, acc):
        if j == len(lengths):
            if not any(left):
                out.append(to_masks(acc))
            return
        avail = [i for i in range(n) if left[i] > 0]
        for sub in itertools.combinations(avail, lengths[j]):
            for i in sub:
                left[i] -= 1
            if all(left[i] <= len(lengths) - j - 1 for i in range(n)):
                rec(j + 1, left, acc + [sub])
            for i in sub:
                left[i] += 1
    rec(0, list(content), [])
    return out


def raw_rank(n, signed):
    """The rank of the unprojected Koszul flattening of the permanent (or determinant) tensor on W_lambda, modulo the
    first prime, over the blocks of content (one per orbit)."""
    p = PRIMES[0]
    lam = staircase(n)
    total = 0
    dim = 0
    for nu, orbit in class_contents([list(range(n))], sum(lam), n - 1):
        tuples = w_tuples(n, nu)
        if not tuples:
            continue
        index = {pack(t, n): i for i, t in enumerate(tuples)}
        mat = np.zeros((len(tuples), len(tuples)), dtype=np.int64)
        for a, t in enumerate(tuples):
            for tup, coef in image_perm(t, n, signed).items():
                mat[a, index[tup]] = coef % p
        total += orbit * rank_mod(mat, p)
        dim += orbit * len(tuples)
    return total, dim


# --- the run ---------------------------------------------------------------------------------------------------------

def conditions(per, power, power_reach, polar):
    """Each condition True, False, or None when the computation could not settle it."""
    c1 = all(per[n]["rank"] == 2 ** math.comb(n, 2) for n in N_TEST)
    c2 = True
    for n in N_TEST:
        bound = 2 ** math.comb(n - 1, 2)
        if power[n] > bound:
            c2 = False
            break
        if power_reach[n] != bound:
            c2 = None
    c3 = all(polar.values())
    return {"the flattening of x1...xn has full rank 2^C(n,2) for n = 2 to 7": c1,
            "the flattening of x1^n has rank at most 2^C(n-1,2) for n = 2 to 7": c2,
            "the polarization identity holds for n = 2 to 8": c3}


def listing(d):
    return ", ".join(str(d[n]) for n in sorted(d))


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    raw = read_bytes(os.path.join(inputs, INPUTS["eprint"][0]), INPUTS["eprint"][1])
    check_source(tex_of(raw))
    points = Points(seed)

    per, power, power_reach, twin = {}, {}, {}, {}
    detail_blocks = {}
    for n in N_TEST:
        rank, blocks = flattening_rank(n, lambda t, n=n: image_perm(t, n, False), [list(range(n))], points)
        per[n] = {"rank": rank, "short": [list(b["content"]) for b in blocks if b["rank"] < b["K"]]}
        cls = [[0], list(range(1, n))]
        prank, pblocks = flattening_rank(n, lambda t, n=n: image_terms(t, n, power_terms(n)), cls, points)
        power[n] = prank
        lam = staircase(n)
        power_reach[n] = sum(orbit * kostka(lam, tuple(sorted(nu[:1] + tuple(x for x in nu[1:]), reverse=True)))
                             for nu, orbit in class_contents(cls, sum(lam), n - 1) if nu[0] == n - 1)
        detail_blocks[str(n)] = {"per": [{"content": list(b["content"]), "orbit": b["orbit"], "K": b["K"],
                                          "rank": b["rank"]} for b in blocks],
                                 "power": [{"content": list(b["content"]), "orbit": b["orbit"], "K": b["K"],
                                            "rank": b["rank"]} for b in pblocks if b["rank"]]}
    for n in N_SMALL:
        cls = [[0], [1], list(range(2, n))] if n > 2 else [[0], [1]]
        twin[n], _ = flattening_rank(n, lambda t, n=n: image_terms(t, n, twin_terms(n)), cls, points)
    polar = {n: polarization_holds(n) for n in N_POLAR}

    dets = {n: det_scalar(n, points) for n in N_SMALL}
    raws = {n: (raw_rank(n, False), raw_rank(n, True)) for n in N_SMALL}
    basis = {n: basis_independent(n, points) for n in N_SMALL}
    agree = True
    for n in N_AGREE:
        lam = staircase(n)
        for nu, _ in class_contents([list(range(n))], sum(lam), n - 1):
            for t in w_tuples(n, nu):
                agree = agree and image_perm(t, n, False) == image_terms(t, n, perm_terms(n, False)) \
                    and image_perm(t, n, True) == image_terms(t, n, perm_terms(n, True))
    weyl = all(sum(orbit * kostka(staircase(n), tuple(sorted(nu, reverse=True)))
                   for nu, orbit in class_contents([list(range(n))], sum(staircase(n)), n - 1))
               == weyl_dimension(staircase(n), n) == 2 ** math.comb(n, 2) for n in N_TEST)
    controls = {"both primes pass Miller-Rabin": all(is_prime(p) for p in PRIMES),
                "the Kostka numbers sum to the Weyl dimension 2^C(n,2) for n = 2 to 7": weyl,
                "the projected tableaux of every block are independent for n = 2 to 6": all(basis.values()),
                "Psi(det_n) is a scalar multiple of the identity for n = 2 to 6": all(dets[n] is not None
                                                                                     for n in N_SMALL),
                "the recursion and the term list give the same flattenings for n = 2 to 5": agree,
                "x1^(n-1) x2 (border rank 2) has at most twice the rank of x1^n for n = 2 to 6":
                    all(twin[n] <= 2 * power[n] for n in N_SMALL)}
    cond = conditions(per, power, power_reach, polar)
    met = sum(1 for v in cond.values() if v is True)
    bounds = {n: (2 ** math.comb(n, 2)) // (2 ** math.comb(n - 1, 2)) if per[n]["rank"] == 2 ** math.comb(n, 2)
              else None for n in N_TEST}
    values = {
        "source": "the e-print holds the theorem, the shapes, both flattening bounds, both ranks, the identity and the table",
        "per_ranks": "rank of F(x1...xn), n = 2 to 7: " + listing({n: per[n]["rank"] for n in N_TEST})
                     + " (2^C(n,2): " + listing({n: 2 ** math.comb(n, 2) for n in N_TEST}) + ")",
        "power_ranks": "rank of F(x1^n), n = 2 to 7: " + listing(power) + " (2^C(n-1,2): "
                       + listing({n: 2 ** math.comb(n - 1, 2) for n in N_TEST}) + ")",
        "power_reach": "dimension of the weights x1^n can reach, n = 2 to 7: " + listing(power_reach),
        "bounds": ("border Waring rank of x1...xn at least " + listing(bounds) + " for n = 2 to 7; the table's earlier "
                   "bounds for n = 3 to 7: " + listing(PREVIOUS)),
        "polarization": "the identity holds exactly for n = 2 to 8: " + ("yes" if all(polar.values()) else
                        "no (n = " + ", ".join(str(n) for n, ok in polar.items() if not ok) + ")"),
        "det_scalars": "Psi(det_n) = c Id, c for n = 2 to 6: " + listing(dets),
        "twin_ranks": "rank of F(x1^(n-1) x2), n = 2 to 6: " + listing(twin),
        "raw_ranks": ("unprojected Koszul flattening on W, n = 2 to 6: permanent " + listing({n: raws[n][0][0] for n in N_SMALL})
                      + "; determinant " + listing({n: raws[n][1][0] for n in N_SMALL}) + "; dim W "
                      + listing({n: raws[n][0][1] for n in N_SMALL})),
        "blocks": ("dominant blocks for x1...xn, n = 2 to 7: " + listing({n: len(detail_blocks[str(n)]["per"]) for n in N_TEST})
                   + "; largest K: " + listing({n: max(b["K"] for b in detail_blocks[str(n)]["per"]) for n in N_TEST})),
        "basis": "projected tableaux independent in every block, n = 2 to 6: " + ("yes" if all(basis.values()) else "no"),
        "conditions_met": met, "conditions_total": len(cond),
        "test_passed": int(all(v is True for v in cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": {k: {"name": nm, "sha256": s} for k, (nm, s) in INPUTS.items()},
              "conditions": {k: v for k, v in cond.items()}, "controls": controls, "blocks": detail_blocks,
              "per": {str(n): per[n] for n in N_TEST}, "power": {str(n): power[n] for n in N_TEST},
              "power_reach": {str(n): power_reach[n] for n in N_TEST}, "twin": {str(n): twin[n] for n in N_SMALL},
              "polarization": {str(n): polar[n] for n in N_POLAR}, "det_scalars": {str(n): dets[n] for n in N_SMALL},
              "raw": {str(n): {"permanent": raws[n][0], "determinant": raws[n][1]} for n in N_SMALL},
              "bounds": {str(n): bounds[n] for n in N_TEST}, "previous": {str(k): v for k, v in PREVIOUS.items()},
              "primes": list(PRIMES), "extra_points": EXTRA}
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
        sys.exit(f"han: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
