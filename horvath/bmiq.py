"""Horvath's normalisation (BMIQcalibration, Additional file 24 of Horvath 2013) ported from R to numpy, with the parts
of R it leans on ported too, so that it gives what R gives.

BMIQcalibration fits a three-state beta mixture (unmethylated, hemimethylated, methylated) to the gold standard and
to each sample by EM, and maps each sample's values onto the gold standard's distributions, state by state. Its
arithmetic is R's, and four pieces of R are ported here exactly, because the result depends on them:

- R's random numbers: set.seed(1) then sample(1:n, k) chooses the 20,000 probes each EM fit uses. R's Mersenne
  Twister, its seeding (the initial scrambling with 69069), and sample()'s rule before R 3.6.0 ("Rounding": floor(n
  u)) reproduce the printed values of Horvath's tutorial (the newer "Rejection" rule moves them in the fourth decimal).
- optim(): Nelder-Mead (nmmin, used by Horvath's blc2 with maxit = 50) and BFGS (vmmin, used by RPMM's blc for the
  gold standard, with optim's central-difference gradient, ndeps = 1e-3), from R's src/appl/optim.c and
  src/library/stats/src/optim.c, step for step, including what each returns when it stops.
- density() with its defaults (bandwidth nrd0, Gaussian kernel, 512 points, cut = 3: linear binning, FFT
  convolution, linear interpolation), whose maximum locates each state's mode.
- sum(): R adds doubles in long double, one after another; numpy's cumsum on longdouble does the same.

Two quirks of the R code are kept, since they are what it does: mean(max(A), min(B)) is mean(x = max(A), trim =
min(B)), which is max(A), so each state's threshold is the largest value of the state below it; and the hemimethylated
probes are moved by a linear map (with the left tail of the methylated state), not by quantiles.

pbeta and qbeta are scipy's regularised incomplete beta and its inverse (the upper tails by symmetry, I_{1-x}(b, a)),
and dbeta(log = TRUE) is (a - 1) log x + (b - 1) log1p(-x) - lbeta(a, b); R computes the last differently for a, b > 2,
which changes values in their last digits only.
"""

import math

import numpy as np
from scipy import special

# ---------------------------------------------------------------- R's random numbers

N_MT, M_MT = 624, 397


class RRandom:
    """R's Mersenne Twister as set.seed() leaves it, and sample() without replacement by the pre-3.6.0 rule."""

    def __init__(self, seed):
        s = seed & 0xFFFFFFFF
        for _ in range(50):                                  # RNG_Init: the initial scrambling
            s = (69069 * s + 1) & 0xFFFFFFFF
        state = []
        for _ in range(N_MT + 1):                            # dummy[0] (mti) then mt[0..623]
            s = (69069 * s + 1) & 0xFFFFFFFF
            state.append(s)
        self.mt = state[1:]
        self.mti = N_MT                                      # FixupSeeds: dummy[0] = 624

    def _genrand(self):
        mt = self.mt
        if self.mti >= N_MT:
            for kk in range(N_MT):
                y = (mt[kk] & 0x80000000) | (mt[(kk + 1) % N_MT] & 0x7FFFFFFF)
                mt[kk] = mt[(kk + M_MT) % N_MT] ^ (y >> 1) ^ (0x9908B0DF if y & 1 else 0)
            self.mti = 0
        y = mt[self.mti]
        self.mti += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        y ^= y >> 18
        return y * 2.3283064365386963e-10

    def unif_rand(self):
        x = self._genrand()
        i2_32m1 = 2.328306437080797e-10                      # 1/(2^32 - 1), fixup()
        if x <= 0.0:
            return 0.5 * i2_32m1
        if 1.0 - x <= 0.0:
            return 1.0 - 0.5 * i2_32m1
        return x

    def sample(self, n, k):
        """sample(1:n, k) as R before 3.6.0 drew it: 1-based values, in the order drawn."""
        x = list(range(n))
        out = []
        for _ in range(k):
            j = int(math.floor(n * self.unif_rand()))
            out.append(x[j] + 1)
            n -= 1
            x[j] = x[n]
        return out


def r_sample(n, k, seed=1):
    return RRandom(seed).sample(n, k)


# ---------------------------------------------------------------- R's sum and mean

def rsum(x):
    """sum(x, na.rm = TRUE): long double, one term after another."""
    x = np.asarray(x, dtype=np.float64)
    x = x[~np.isnan(x)]
    if x.size == 0:
        return 0.0
    s = np.cumsum(x.astype(np.longdouble))[-1]
    if s > np.finfo(np.float64).max:
        return math.inf
    if s < -np.finfo(np.float64).max:
        return -math.inf
    return float(s)


def rmean(x):
    """mean(x): long double sum over n, then the mean of the residuals added (R's two-pass mean)."""
    x = np.asarray(x, dtype=np.float64).astype(np.longdouble)
    n = x.size
    s = np.cumsum(x)[-1] / n
    if math.isfinite(float(s)):
        t = np.cumsum(x - s)[-1]
        s = s + t / n
    return float(s)


# ---------------------------------------------------------------- density() and its mode

def _quantile7(a, q):
    """quantile(x, q, type = 7) on sorted a, in R's arithmetic: (1 - h) x[lo] + h x[hi]."""
    index = 1 + (a.size - 1) * q
    lo, hi = math.floor(index), math.ceil(index)
    qs = float(a[lo - 1])
    if index > lo and a[hi - 1] != qs:
        h = index - lo
        qs = (1 - h) * qs + h * float(a[hi - 1])
    return qs


def r_var(x):
    """var(x): R's two-pass mean, then the squared deviations summed in long double."""
    xm = rmean(x)
    d = (x - xm) * (x - xm)
    return float(np.cumsum(d.astype(np.longdouble))[-1] / (x.size - 1))


def bw_nrd0(x):
    if x.size < 2:
        raise ValueError("need at least 2 data points")
    a = np.sort(x)
    hi = math.sqrt(r_var(x))
    lo = min(hi, (_quantile7(a, 0.75) - _quantile7(a, 0.25)) / 1.34)
    if not lo:
        lo = hi or abs(float(x[0])) or 1.0
    return 0.9 * lo * x.size ** (-0.2)


def seq_len_out(a, b, n):
    """seq.int(a, b, length.out = n), as R 4.3 computes it."""
    out = a + np.arange(n, dtype=np.float64) * ((b - a) / (n - 1))
    out[0], out[-1] = a, b
    return out


def bin_dist(x, lo, hi, n):
    """massdist.c BinDist with weights 1/N: linear binning on 2n cells, the upper half zero."""
    y = np.zeros(2 * n)
    w = 1.0 / x.size
    delta = (hi - lo) / (n - 1)
    for xi in x:                                             # kept as a loop: += order as in C
        pos = (xi - lo) / delta
        ix = math.floor(pos)
        fx = pos - ix
        if 0 <= ix <= n - 2:
            y[ix] += (1 - fx) * w
            y[ix + 1] += fx * w
        elif ix == -1:
            y[0] += fx * w
        elif ix == n - 1:
            y[ix] += (1 - fx) * w
    return y


def approx_linear(xs, ys, v):
    """approx(xs, ys, v)$y for increasing xs (approx1 in R's approx.c), NA outside."""
    out = np.empty(v.size)
    n = xs.size
    for t, vt in enumerate(v):
        if vt < xs[0] or vt > xs[-1]:
            out[t] = math.nan
            continue
        i, j = 0, n - 1
        while i < j - 1:
            ij = (i + j) // 2
            if vt < xs[ij]:
                j = ij
            else:
                i = ij
        if vt == xs[j]:
            out[t] = ys[j]
        elif vt == xs[i]:
            out[t] = ys[i]
        else:
            out[t] = ys[i] + (ys[j] - ys[i]) * ((vt - xs[i]) / (xs[j] - xs[i]))
    return out


M_1_SQRT_2PI = 0.398942280401432677939946059934


def density_mode(x, n=512, cut=3.0):
    """d$x[which.max(d$y)] for d = density(x) with R's defaults."""
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    bw = bw_nrd0(x)
    frm, to = float(x.min()) - cut * bw, float(x.max()) + cut * bw
    lo, up = frm - 4 * bw, to + 4 * bw
    y = bin_dist(x, lo, up, n)
    kords = seq_len_out(0.0, 2 * (up - lo), 2 * n)
    kords[n + 1:2 * n] = -kords[n - 1:0:-1]
    z = kords / bw
    kords = (M_1_SQRT_2PI * np.exp(-0.5 * z * z)) / bw                       # dnorm(kords, sd = bw)
    conv = np.fft.ifft(np.fft.fft(y) * np.conj(np.fft.fft(kords))) * (2 * n)   # R's inverse fft is unnormalised
    kords = np.maximum(0.0, conv.real[:n] / (2 * n))
    xords = seq_len_out(lo, up, n)
    grid = seq_len_out(frm, to, n)
    dens = approx_linear(xords, kords, grid)
    return float(grid[int(np.nanargmax(dens))])


# ---------------------------------------------------------------- optim(): Nelder-Mead and BFGS

class OptimError(Exception):
    """An error optim() raises, which betaEst catches with try() and answers with c(1, 1)."""


BIG = 1.0e35
RELTOL = 1.4901161193847656e-08            # sqrt(.Machine$double.eps)


def nmmin(fn, bvec, maxit, alpha=1.0, bet=0.5, gamm=2.0, abstol=-math.inf, intol=RELTOL):
    """R's nmmin: the best vertex when it stops."""
    n = len(bvec)
    bvec = list(bvec)
    if maxit <= 0:
        return bvec
    f = fn(bvec)
    if not math.isfinite(f):
        raise OptimError("function cannot be evaluated at initial parameters")
    funcount = 1
    convtol = intol * (abs(f) + intol)
    n1, C = n + 1, n + 2
    P = [[0.0] * (n + 2) for _ in range(n + 1)]
    P[n1 - 1][0] = f
    for i in range(n):
        P[i][0] = bvec[i]
    L = 1
    size = 0.0
    step = 0.0
    for i in range(n):
        if 0.1 * abs(bvec[i]) > step:
            step = 0.1 * abs(bvec[i])
    if step == 0.0:
        step = 0.1
    for j in range(2, n1 + 1):
        for i in range(n):
            P[i][j - 1] = bvec[i]
        trystep = step
        while P[j - 2][j - 1] == bvec[j - 2]:
            P[j - 2][j - 1] = bvec[j - 2] + trystep
            trystep *= 10
        size += trystep
    oldsize = size
    calcvert = True
    while True:
        if calcvert:
            for j in range(n1):
                if j + 1 != L:
                    for i in range(n):
                        bvec[i] = P[i][j]
                    f = fn(bvec)
                    if not math.isfinite(f):
                        f = BIG
                    funcount += 1
                    P[n1 - 1][j] = f
            calcvert = False
        VL = P[n1 - 1][L - 1]
        VH = VL
        H = L
        for j in range(1, n1 + 1):
            if j != L:
                f = P[n1 - 1][j - 1]
                if f < VL:
                    L, VL = j, f
                if f > VH:
                    H, VH = j, f
        if VH <= VL + convtol or VL <= abstol:
            break
        for i in range(n):
            temp = -P[i][H - 1]
            for j in range(n1):
                temp += P[i][j]
            P[i][C - 1] = temp / n
        for i in range(n):
            bvec[i] = (1.0 + alpha) * P[i][C - 1] - alpha * P[i][H - 1]
        f = fn(bvec)
        if not math.isfinite(f):
            f = BIG
        funcount += 1
        VR = f
        if VR < VL:
            P[n1 - 1][C - 1] = f
            for i in range(n):
                f = gamm * bvec[i] + (1 - gamm) * P[i][C - 1]
                P[i][C - 1] = bvec[i]
                bvec[i] = f
            f = fn(bvec)
            if not math.isfinite(f):
                f = BIG
            funcount += 1
            if f < VR:
                for i in range(n):
                    P[i][H - 1] = bvec[i]
                P[n1 - 1][H - 1] = f
            else:
                for i in range(n):
                    P[i][H - 1] = P[i][C - 1]
                P[n1 - 1][H - 1] = VR
        else:
            if VR < VH:
                for i in range(n):
                    P[i][H - 1] = bvec[i]
                P[n1 - 1][H - 1] = VR
            for i in range(n):
                bvec[i] = (1 - bet) * P[i][H - 1] + bet * P[i][C - 1]
            f = fn(bvec)
            if not math.isfinite(f):
                f = BIG
            funcount += 1
            if f < P[n1 - 1][H - 1]:
                for i in range(n):
                    P[i][H - 1] = bvec[i]
                P[n1 - 1][H - 1] = f
            elif VR >= VH:
                calcvert = True
                size = 0.0
                for j in range(n1):
                    if j + 1 != L:
                        for i in range(n):
                            P[i][j] = bet * (P[i][j] - P[i][L - 1]) + P[i][L - 1]
                            size += abs(P[i][j] - P[i][L - 1])
                if size < oldsize:
                    oldsize = size
                else:
                    break                                    # fail = 10: polytope size not decreased
        if funcount > maxit:
            break
    return [P[i][L - 1] for i in range(n)]


def numgrad(fn, p, ndeps=1e-3):
    """optim's fmingr without a gradient: central differences, ndeps each way."""
    df = []
    x = list(p)
    for i in range(len(p)):
        x[i] = p[i] + ndeps
        val1 = fn(x)
        x[i] = p[i] - ndeps
        val2 = fn(x)
        d = (val1 - val2) / (2 * ndeps)
        if not math.isfinite(d):
            raise OptimError(f"non-finite finite-difference value [{i + 1}]")
        df.append(d)
        x[i] = p[i]
    return df


def vmmin(fn, b, maxit=100, abstol=-math.inf, reltol=RELTOL):
    """R's vmmin with the numerical gradient: the parameters it holds when it stops (as optim returns them)."""
    stepredn, acctol, reltest = 0.2, 0.0001, 10.0
    n = len(b)
    b = list(b)
    if maxit <= 0:
        return b

    def f_at(v):
        for t in v:
            if not math.isfinite(t):
                raise OptimError("non-finite value supplied by optim")
        return fn(v)

    f = f_at(b)
    if not math.isfinite(f):
        raise OptimError("initial value in 'vmmin' is not finite")
    Fmin = f
    funcount = gradcount = 1
    g = numgrad(f_at, b)
    it = 1
    ilast = gradcount
    B = [[0.0] * n for _ in range(n)]
    t = [0.0] * n
    X = [0.0] * n
    c = [0.0] * n
    while True:
        if ilast == gradcount:
            for i in range(n):
                for j in range(i):
                    B[i][j] = 0.0
                B[i][i] = 1.0
        for i in range(n):
            X[i] = b[i]
            c[i] = g[i]
        gradproj = 0.0
        for i in range(n):
            s = 0.0
            for j in range(i + 1):
                s -= B[i][j] * g[j]
            for j in range(i + 1, n):
                s -= B[j][i] * g[j]
            t[i] = s
            gradproj += s * g[i]
        if gradproj < 0.0:
            steplength = 1.0
            accpoint = False
            while True:
                count = 0
                for i in range(n):
                    b[i] = X[i] + steplength * t[i]
                    if reltest + X[i] == reltest + b[i]:
                        count += 1
                if count < n:
                    f = f_at(b)
                    funcount += 1
                    accpoint = math.isfinite(f) and (f <= Fmin + gradproj * steplength * acctol)
                    if not accpoint:
                        steplength *= stepredn
                if count == n or accpoint:
                    break
            enough = (f > abstol) and abs(f - Fmin) > reltol * (abs(Fmin) + reltol)
            if not enough:
                count = n
                Fmin = f
            if count < n:
                Fmin = f
                g = numgrad(f_at, b)
                gradcount += 1
                it += 1
                D1 = 0.0
                for i in range(n):
                    t[i] = steplength * t[i]
                    c[i] = g[i] - c[i]
                    D1 += t[i] * c[i]
                if D1 > 0:
                    D2 = 0.0
                    for i in range(n):
                        s = 0.0
                        for j in range(i + 1):
                            s += B[i][j] * c[j]
                        for j in range(i + 1, n):
                            s += B[j][i] * c[j]
                        X[i] = s
                        D2 += s * c[i]
                    D2 = 1.0 + D2 / D1
                    for i in range(n):
                        for j in range(i + 1):
                            B[i][j] += (D2 * t[i] * t[j] - X[i] * t[j] - t[i] * X[j]) / D1
                else:
                    ilast = gradcount
            else:
                if ilast < gradcount:
                    count = 0
                    ilast = gradcount
        else:
            count = 0
            if ilast == gradcount:
                count = n
            else:
                ilast = gradcount
        if it >= maxit:
            break
        if gradcount - ilast > 2 * n:
            ilast = gradcount
        if not (count != n or ilast != gradcount):
            break
    return b


# ---------------------------------------------------------------- the beta mixture (RPMM's blc, Horvath's blc2)

def dbeta_log(y, a, b):
    if not (math.isfinite(a) and math.isfinite(b)) or a <= 0 or b <= 0:
        return np.full(y.shape, -math.inf)
    return (a - 1) * np.log(y) + (b - 1) * np.log1p(-y) - special.betaln(a, b)


def r_log(x):
    return math.log(x) if x > 0 else (-math.inf if x == 0 else math.nan)


def r_div(a, b):
    """a / b with IEEE results, as R gives them, where Python would raise."""
    if b == 0:
        return math.nan if (a == 0 or math.isnan(a)) else math.copysign(math.inf, a) * math.copysign(1.0, b)
    return a / b


def r_exp(x):
    """exp() as R has it: Inf on overflow, not an error."""
    try:
        return math.exp(x)
    except OverflowError:
        return math.inf


def r_pmax(a, x):
    return math.nan if math.isnan(x) else max(a, x)


def beta_objf(logab, y, w):
    a, b = r_exp(logab[0]), r_exp(logab[1])
    with np.errstate(invalid="ignore", over="ignore"):
        return -rsum(w * dbeta_log(y, a, b))


def beta_est(y, w, method):
    """RPMM's betaEst (BFGS) or Horvath's betaEst2 (Nelder-Mead, maxit 50); weights are 1."""
    if y.size <= 1:
        return 1.0, 1.0
    N = rsum(w)
    p = r_div(rsum(w * y), N)
    v = r_div(rsum(w * y * y), N) - p * p
    ratio = r_div(p * (1 - p), v) - 1
    k = r_log(r_pmax(1e-06, ratio))
    logab = [r_log(p) + k, r_log(1 - p) + k]
    if y.size == 2:
        return r_exp(logab[0]), r_exp(logab[1])
    fn = lambda la: beta_objf(la, y, w)                     # noqa: E731
    try:
        if not all(math.isfinite(t) for t in logab):
            raise OptimError("non-finite initial parameters")
        par = vmmin(fn, logab) if method == "BFGS" else nmmin(fn, logab, maxit=50)
    except OptimError:
        return 1.0, 1.0
    return r_exp(par[0]), r_exp(par[1])


def blc(Y, w, maxiter, tol, method):
    """RPMM's blc (method "BFGS") or Horvath's blc2 ("Nelder-Mead") for one column Y: a, b, eta, mu and w."""
    Ymn = float(Y[Y > 0].min())
    Ymx = float(Y[Y < 1].max())
    Y = np.maximum(Y, Ymn / 2)
    Y = np.minimum(Y, 1 - (1 - Ymx) / 2)
    n, K = w.shape
    a = np.full(K, math.inf)
    b = np.full(K, math.inf)
    mu = np.full(K, math.inf)
    eta = None
    for _ in range(maxiter):
        eta = np.array([rsum(w[:, k]) for k in range(K)]) / n
        mu0 = mu.copy()
        for k in range(K):
            ak, bk = beta_est(Y, w[:, k], method)
            a[k], b[k] = ak, bk
            mu[k] = r_div(ak, ak + bk)
        ww = np.column_stack([dbeta_log(Y, a[k], b[k]) for k in range(K)])
        ww = np.where(np.isnan(ww), 0.0, ww)                # apply(ww, c(1,3), sum, na.rm = TRUE)
        wmax = ww.max(axis=1)
        ww = ww - wmax[:, None]
        ww = eta[None, :] * np.exp(ww)
        acc = ww[:, 0].astype(np.longdouble)
        for k in range(1, K):
            acc = acc + ww[:, k]                            # apply(w, 1, sum): long double, in order
        like = acc.astype(np.float64)
        w = (1.0 / like)[:, None] * ww
        crit = float(np.max(np.abs(mu - mu0)))
        if crit < tol:
            break
    return {"a": a.copy(), "b": b.copy(), "eta": eta, "mu": mu.copy(), "w": w}


# ---------------------------------------------------------------- BMIQcalibration

NL, NFIT, TH1, NITER, TOL = 3, 20000, (0.2, 0.75), 5, 0.001


def _max_class(values, classes, k):
    sel = values[classes == k]
    return float(sel.max()) if sel.size else -math.inf


def _min_class(values, classes, k):
    sel = values[classes == k]
    return float(sel.min()) if sel.size else math.inf


def r_mean_trim(x, trim):
    """mean(x, trim) for a single value x, as R's mean.default gives it: x (or NA when trim is NA)."""
    if isinstance(trim, float) and math.isnan(trim):
        return math.nan
    return x


def initial_weights(beta, th):
    w0 = np.zeros((beta.size, NL))
    w0[beta <= th[0], 0] = 1
    w0[(beta > th[0]) & (beta <= th[1]), 1] = 1
    w0[beta > th[1], 2] = 1
    return w0


_SAMPLES = {}


def sample_indices(n):
    """set.seed(1); sample(1:n, min(NFIT, n)) - 1, kept: every fit of n values draws the same."""
    if n not in _SAMPLES:
        _SAMPLES[n] = np.array(r_sample(n, min(NFIT, n)), dtype=np.int64) - 1
    return _SAMPLES[n]


def gold_fit(gold):
    """The gold standard's side of BMIQcalibration, done once: its mixture, thresholds and modes."""
    gold = np.asarray(gold, dtype=np.float64)
    w0 = initial_weights(gold, TH1)
    idx = sample_indices(gold.size)
    em1 = blc(gold[idx].copy(), w0[idx].copy(), NITER, TOL, "BFGS")
    sub = np.argmax(em1["w"], axis=1) + 1
    g = gold[idx]
    th = (r_mean_trim(_max_class(g, sub, 1), _min_class(g, sub, 2)),
          r_mean_trim(_max_class(g, sub, 2), _min_class(g, sub, 3)))
    cls = np.full(gold.size, 2)
    cls[gold < th[0]] = 1
    cls[gold > th[1]] = 3
    mod = {}
    for k, name in ((1, "U"), (3, "M")):
        sel = gold[cls == k]
        mod[name] = float(sel[0]) if sel.size == 1 else density_mode(sel)
    return {"em": em1, "th": th, "mod": mod, "idx": idx}


def calibrate_unit_interval(beta):
    lo, hi = float(np.nanmin(beta)), float(np.nanmax(beta))
    if (lo < 0 or hi > 1) and math.isfinite(lo) and math.isfinite(hi):
        slope = (0.999 - 0.001) / (hi - lo)
        return 0.001 - slope * lo + slope * beta
    return beta


def normalise(beta, gf):
    """One sample (its 21,368 values, gold standard order) through BMIQcalibration's loop."""
    beta2 = calibrate_unit_interval(np.asarray(beta, dtype=np.float64))
    mod2U = density_mode(beta2[beta2 < 0.4])
    mod2M = density_mode(beta2[beta2 > 0.6])
    th2 = (gf["th"][0] + (mod2U - gf["mod"]["U"]), gf["th"][1] + (mod2M - gf["mod"]["M"]))
    w0 = initial_weights(beta2, th2)
    idx = sample_indices(beta2.size)
    em2 = blc(beta2[idx].copy(), w0[idx].copy(), NITER, TOL, "Nelder-Mead")
    sub = np.argmax(em2["w"], axis=1) + 1
    s = beta2[idx]
    if np.any(sub == 2):
        th = (r_mean_trim(_max_class(s, sub, 1), _min_class(s, sub, 2)),
              r_mean_trim(_max_class(s, sub, 2), _min_class(s, sub, 3)))
    else:
        th = (0.5 * _max_class(s, sub, 1) + 0.5 * rmean(s[sub == 3]),
              1 / 3 * _max_class(s, sub, 1) + 2 / 3 * rmean(s[sub == 3]))
    cls = np.full(beta2.size, 2)
    cls[beta2 <= th[0]] = 1
    cls[beta2 >= th[1]] = 3
    em1 = gf["em"]
    av2 = em2["mu"]
    nbeta = beta2.copy()
    selU = np.flatnonzero(cls == 1)
    selUR = selU[beta2[selU] > av2[0]]
    selUL = selU[beta2[selU] < av2[0]]
    a1, b1, a2, b2 = em1["a"][0], em1["b"][0], em2["a"][0], em2["b"][0]
    nbeta[selUR] = 1 - special.betaincinv(b1, a1, special.betainc(b2, a2, 1 - beta2[selUR]))
    nbeta[selUL] = special.betaincinv(a1, b1, special.betainc(a2, b2, beta2[selUL]))
    selM = np.flatnonzero(cls == 3)
    selMR = selM[beta2[selM] > av2[2]]
    selML = selM[beta2[selM] < av2[2]]
    a1, b1, a2, b2 = em1["a"][2], em1["b"][2], em2["a"][2], em2["b"][2]
    nbeta[selMR] = 1 - special.betaincinv(b1, a1, special.betainc(b2, a2, 1 - beta2[selMR]))
    selH = np.concatenate([np.flatnonzero(cls == 2), selML])
    minH, maxH = float(beta2[selH].min()), float(beta2[selH].max())
    deltaH = maxH - minH
    deltaUH = -float(beta2[selU].max()) + minH
    deltaHM = -maxH + float(beta2[selMR].min())
    nmaxH = float(nbeta[selMR].min()) - deltaHM
    nminH = float(nbeta[selU].max()) + deltaUH
    hf = (nmaxH - nminH) / deltaH
    nbeta[selH] = nminH + hf * (beta2[selH] - minH)
    return nbeta, {"mod2": (mod2U, mod2M), "th2": th2, "th": th, "em2": {k: em2[k].tolist() for k in ("a", "b", "eta", "mu")},
                   "classes": [int((cls == k).sum()) for k in (1, 2, 3)], "hf": hf}
