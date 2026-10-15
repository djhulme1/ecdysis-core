"""Integrated information from the decoding perspective: Oizumi et al. (2016)'s Phi*, bounded below and above.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:cb7b7cff972641ce) is from Oizumi, Amari,
Yanagawa, Fujii and Tsuchiya, "Measuring Integrated Information from the Decoding Perspective", PLoS Computational
Biology 12(1), e1004654 (2016; CC BY), its abstract: "We show that Phi* is properly bounded from below and above, as
required, as a measure of integrated information." The bounds it requires (its Eq 4, which IIT 2.0's Phi meets):
0 <= Phi <= I(X^{t-tau}; X^t), and Phi = 0 when the system generates no information or comprises independent parts.
Phi* = I - I* (its Eq 9), where I* is the "hypothetical" information of mismatched decoding that ignores the
interactions between parts, maximised over beta; it meets the bounds, the paper says, "because I* is greater than or
equal to 0 and is less than or equal to the information in the whole system I".
Under the Gaussian assumption (its Methods, Eqs 22-28):
  I = (1/2) log |Sigma(X^{t-tau})| / |Sigma(X^{t-tau} | X^t)|,
  I*(beta) = (1/2) Tr[Sigma(X^t) R] + (1/2) log |Q| |Sigma(X^{t-tau})| - beta N / 2,
  Q = Sigma(X^{t-tau})^-1 + beta S_D(X^{t-tau})^-1 S_D(X^t, X^{t-tau})^T S_D(X^t | X^{t-tau})^-1 S_D(X^t, X^{t-tau})
      S_D(X^{t-tau})^-1,
  R = beta S_D(X^t | X^{t-tau})^-1 - beta^2 S_D(X^t | X^{t-tau})^-T S_D(X^t, X^{t-tau}) S_D(X^{t-tau})^-1 Q^-1
      S_D(X^{t-tau})^-1 S_D(X^t, X^{t-tau})^T S_D(X^t | X^{t-tau})^-1,
where S_D(.) is block diagonal, each block the covariance (cross covariance, conditional covariance) of one part
alone. Its worked model (Eqs 13-16): X^t = A X^{t-1} + E^t with A = a [[1, 1], [1, 1]], Sigma(E) = [[1, c], [c, 1]],
tau = 1, and the steady state Sigma(X) = A Sigma(X) A^T + Sigma(E); its Figure 3 varies c from 0 to 1 at a = 0 (no
information: Phi* and Phi_I stay 0 while Phi_H rises) and at a = 0.4 (Phi_I falls below 0 as c nears 1).

Rules, committed before Phi* was computed on any system the test names:

1. The quantities: as above, in natural logarithms, for the autoregressive model X^t = A X^{t-1} + E^t at its steady
   state (tau = 1), so that Sigma(X^{t-1}) = Sigma(X^t) = Sigma, Sigma(X^t, X^{t-1}) = A Sigma, Sigma(X^t | X^{t-1})
   = Sigma(E); each part's blocks from that part's own variables alone (its conditional covariance from its own past).
   Plain Python (exact steady state by solving (I - A (x) A) vec Sigma = vec Sigma(E); Gauss-Jordan inverses and LU
   determinants). I* is maximised over beta >= 0 by golden-section search (I*(beta) is concave; the paper solves
   dI*/dbeta = 0, which it calls a quadratic equation in beta), I* being the larger of the search's value and I*(0),
   each as computed (I*(0) is 0 in exact arithmetic). Phi_I = I - sum_i I(M_i^{t-1}; M_i^t) and Phi_H = sum_i H(M_i^{t-1} | M_i^t) - H(X^{t-1} | X^t),
   the two earlier measures the paper sets against Phi*, are computed beside it.
2. Systems: (i) the paper's model at a = 0 and a = 0.4, c from 0 to 0.99 in steps of 0.01, the two units the parts;
   (ii) 2,000 systems drawn from the archive's seed: N from 2 to 6 units, A with entries uniform on [-1, 1] scaled to a
   Frobenius norm uniform on [0.1, 0.95] (so stable), Sigma(E) = L L^T + 0.1 I with L uniform on [-1, 1], and a
   partition into 2 to N non-empty parts drawn uniformly over set partitions with that many parts; (iii) 200 systems
   with independent parts, A and Sigma(E) block diagonal over a drawn partition.
3. The test's conditions, with a tolerance of 1e-9 nats: C1, Phi* >= -1e-9 for every system (the lower bound); C2,
   Phi* <= I + 1e-9 for every system (the upper bound); C3, |Phi*| <= 1e-9 where I = 0 (the paper's model at a = 0)
   and where the parts are independent (iii). The test passes when all three hold.

Beside the test, not counted: Phi* at a = 0.4 for c = 0, 0.5 and 0.9; Phi_H at a = 0, c = 0.9 (the paper: positive,
though I = 0) and Phi_I at a = 0.4, c = 0.99 (the paper: negative); the least and greatest Phi*/I over (ii).

Controls (controls_passed of controls_total):
 (a) Matched decoding: with the whole system as its only part, max I* equals I (within 1e-9) on 200 drawn systems.
 (b) One unit by hand: I*(beta) for X^t = a X^{t-1} + e against its closed form, and I*(1) = I = -(1/2) log(1 - a^2).
 (c) The steady state: |Sigma - A Sigma A^T - Sigma(E)| below 1e-10 on every drawn system.
 (d) The search: on 200 drawn systems no beta of a grid of 401 on [0, 4 beta*] beats the golden-section maximum.
 (e) The paper's Figure 3 for the earlier measures: at a = 0, Phi_I is 0 (within 1e-9) and Phi_H rises with c; at
     a = 0.4, Phi_I < 0 at c = 0.99.
"""

import hashlib
import json
import math
import os
import re
import sys

TOL = 1e-9
N_RANDOM, N_INDEP, N_CONTROL = 2000, 200, 200
TEST = ("Refuted if Phi*, computed by the paper's Gaussian expression (Eqs 22-28) for X^t = A X^{t-1} + E at steady "
        "state, falls below 0 or above I(X^{t-1}; X^t) by more than 1e-9 nats in the paper's model (A = a[[1,1],[1,1]], "
        "noise correlation c, a = 0 and 0.4, c = 0 to 0.99) or in 2,000 seed-drawn stable systems of 2 to 6 units "
        "under drawn partitions; or is not 0 within 1e-9 where I = 0 (a = 0) or the parts are independent.")


class Refused(Exception):
    pass


class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def u64(self):
        self.n += 1
        return int.from_bytes(hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()[:8], "big")

    def uniform(self, lo, hi):
        return lo + (hi - lo) * (self.u64() >> 11) * 2.0 ** -53

    def below(self, m):
        return self.u64() % m


# ---------------------------------------------------------------- small linear algebra

def zeros(n, m=None):
    return [[0.0] * (n if m is None else m) for _ in range(n)]


def eye(n):
    z = zeros(n)
    for i in range(n):
        z[i][i] = 1.0
    return z


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def tr(a):
    return [list(r) for r in zip(*a)]


def add(a, b, s=1.0):
    return [[x + s * y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]


def scale(a, s):
    return [[s * x for x in r] for r in a]


def solve(a, b):
    """Solve a x = b (b a matrix) by Gauss-Jordan elimination with partial pivoting."""
    n = len(a)
    m = [list(ra) + list(rb) for ra, rb in zip(a, b)]
    w = len(m[0])
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-300:
            raise ZeroDivisionError("singular matrix")
        m[col], m[piv] = m[piv], m[col]
        p = m[col][col]
        m[col] = [x / p for x in m[col]]
        for r in range(n):
            if r != col and m[r][col] != 0.0:
                f = m[r][col]
                m[r] = [x - f * y for x, y in zip(m[r], m[col])]
    return [row[n:w] for row in m]


def inv(a):
    return solve(a, eye(len(a)))


def logdet(a):
    """log |a| for a matrix of positive determinant (a covariance), by LU with partial pivoting."""
    n = len(a)
    m = [list(r) for r in a]
    s, sign = 0.0, 1
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if m[piv][col] == 0.0:
            raise ZeroDivisionError("singular matrix")
        if piv != col:
            m[col], m[piv] = m[piv], m[col]
            sign = -sign
        p = m[col][col]
        if p < 0:
            sign = -sign
        s += math.log(abs(p))
        for r in range(col + 1, n):
            f = m[r][col] / p
            if f:
                m[r] = [x - f * y for x, y in zip(m[r], m[col])]
    if sign < 0:
        raise ValueError("determinant not positive")
    return s


def steady(A, SE):
    """Sigma with Sigma = A Sigma A^T + SE, from (I - A (x) A) vec Sigma = vec SE."""
    n = len(A)
    big = zeros(n * n)
    for i in range(n):
        for j in range(n):
            r = i * n + j
            big[r][r] += 1.0
            for k in range(n):
                for l in range(n):
                    big[r][k * n + l] -= A[i][k] * A[j][l]
    v = solve(big, [[SE[i][j]] for i in range(n) for j in range(n)])
    S = [[v[i * n + j][0] for j in range(n)] for i in range(n)]
    return [[(S[i][j] + S[j][i]) / 2 for j in range(n)] for i in range(n)]


def sub(M, idx):
    return [[M[i][j] for j in idx] for i in idx]


def blockdiag(blocks, parts, n):
    z = zeros(n)
    for b, idx in zip(blocks, parts):
        for a_, i in enumerate(idx):
            for c_, j in enumerate(idx):
                z[i][j] = b[a_][c_]
    return z


# ---------------------------------------------------------------- the measures

def system(A, SE):
    S = steady(A, SE)
    C = mul(A, S)                                   # Sigma(X^t, X^{t-1})
    Sp_given = add(S, mul(mul(tr(C), inv(S)), C), -1.0)   # Sigma(X^{t-1} | X^t) = S - C^T S^-1 C
    return S, C, Sp_given


def mutual_info(S, Sp_given):
    return 0.5 * (logdet(S) - logdet(Sp_given))


def part_blocks(S, C, parts):
    n = len(S)
    bS, bC, bK = [], [], []
    for idx in parts:
        s, c = sub(S, idx), sub(C, idx)
        k = add(s, mul(mul(c, inv(s)), tr(c)), -1.0)     # Sigma(M^t | M^{t-1}) from the part's own past
        bS.append(s); bC.append(c); bK.append(k)
    return blockdiag(bS, parts, n), blockdiag(bC, parts, n), blockdiag(bK, parts, n), bS, bC, bK


def istar_fn(S, C, parts):
    n = len(S)
    DS, DC, DK, _, _, _ = part_blocks(S, C, parts)
    DSi, DKi, Si = inv(DS), inv(DK), inv(S)
    left = mul(mul(DSi, tr(DC)), DKi)                  # S_D(past)^-1 S_D(t,past)^T S_D(t|past)^-1
    core = mul(mul(left, DC), DSi)                     # ... S_D(t,past) S_D(past)^-1
    K1 = mul(mul(tr(DKi), DC), DSi)                    # S_D(t|past)^-T S_D(t,past) S_D(past)^-1
    K2 = left                                          # S_D(past)^-1 S_D(t,past)^T S_D(t|past)^-1
    ld_S = logdet(S)

    def f(beta):
        Q = add(Si, scale(core, beta))
        Qi = inv(Q)
        R = add(scale(DKi, beta), mul(mul(K1, Qi), K2), -beta * beta)
        trace = sum(mul(S, R)[i][i] for i in range(n))
        return 0.5 * trace + 0.5 * (logdet(Q) + ld_S) - beta * n / 2
    return f


def maximise(f):
    """Golden-section search for the maximum of a concave f on beta >= 0."""
    lo, hi = 0.0, 1.0
    while f(hi) > f(hi / 2) and hi < 1e6:
        hi *= 2
    g = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    x1, x2 = b - g * (b - a), a + g * (b - a)
    f1, f2 = f(x1), f(x2)
    for _ in range(200):
        if f1 < f2:
            a, x1, f1 = x1, x2, f2
            x2 = a + g * (b - a)
            f2 = f(x2)
        else:
            b, x2, f2 = x2, x1, f1
            x1 = b - g * (b - a)
            f1 = f(x1)
        if b - a < 1e-13 * max(1.0, b):
            break
    beta = (a + b) / 2
    fb, f0 = f(beta), f(0.0)
    return (beta, fb) if fb >= f0 else (0.0, f0)


def measures(A, SE, parts):
    S, C, Sp_given = system(A, SE)
    I = mutual_info(S, Sp_given)
    beta, istar = maximise(istar_fn(S, C, parts))
    _, _, _, bS, bC, bK = part_blocks(S, C, parts)
    parts_I, parts_H = 0.0, 0.0
    for s, c in zip(bS, bC):
        sp_given = add(s, mul(mul(tr(c), inv(s)), c), -1.0)  # Sigma(M^{t-1} | M^t)
        parts_I += 0.5 * (logdet(s) - logdet(sp_given))
        parts_H += 0.5 * logdet(sp_given)
    phi_I = I - parts_I
    phi_H = parts_H - 0.5 * logdet(Sp_given)
    return {"I": I, "phistar": I - istar, "istar": istar, "beta": beta, "phi_I": phi_I, "phi_H": phi_H}


def paper_model(a, c):
    return [[a, a], [a, a]], [[1.0, c], [c, 1.0]], [[0], [1]]


# ---------------------------------------------------------------- drawn systems

def draw_partition(st, n, k):
    """A set partition of range(n) into k non-empty parts, uniform over such partitions (by rejection)."""
    while True:
        labels = [st.below(k) for _ in range(n)]
        if len(set(labels)) == k:
            return [[i for i in range(n) if labels[i] == p] for p in range(k)]


def draw_system(st, independent=False):
    n = 2 + st.below(5)
    k = 2 + st.below(n - 1)
    parts = draw_partition(st, n, k)
    A = [[st.uniform(-1, 1) for _ in range(n)] for _ in range(n)]
    L = [[st.uniform(-1, 1) for _ in range(n)] for _ in range(n)]
    if independent:
        where = {i: p for p, idx in enumerate(parts) for i in idx}
        for i in range(n):
            for j in range(n):
                if where[i] != where[j]:
                    A[i][j] = 0.0
                    L[i][j] = 0.0
    fro = math.sqrt(sum(x * x for r in A for x in r)) or 1.0
    s = st.uniform(0.1, 0.95)
    A = scale(A, s / fro)
    SE = add(mul(L, tr(L)), scale(eye(n), 0.1))
    return A, SE, parts


# ---------------------------------------------------------------- the assessment

def assess(seed):
    viol_lo = viol_hi = 0
    zero_gap = 0.0
    model = {}
    for a in (0.0, 0.4):
        for k in range(100):
            c = k / 100
            m = measures(*paper_model(a, c))
            model[(a, c)] = m
            viol_lo += m["phistar"] < -TOL
            viol_hi += m["phistar"] > m["I"] + TOL
            if a == 0.0:
                zero_gap = max(zero_gap, abs(m["phistar"]))
    st = Stream(seed, "systems")
    ratios = []
    for _ in range(N_RANDOM):
        A, SE, parts = draw_system(st)
        m = measures(A, SE, parts)
        viol_lo += m["phistar"] < -TOL
        viol_hi += m["phistar"] > m["I"] + TOL
        if m["I"] > 1e-6:
            ratios.append(m["phistar"] / m["I"])
    sti = Stream(seed, "independent")
    for _ in range(N_INDEP):
        A, SE, parts = draw_system(sti, independent=True)
        zero_gap = max(zero_gap, abs(measures(A, SE, parts)["phistar"]))
    c1, c2, c3 = viol_lo == 0, viol_hi == 0, zero_gap <= TOL
    cond = {"C1 Phi* >= 0": c1, "C2 Phi* <= I": c2, "C3 Phi* = 0 without information or integration": c3}

    ctl, info = {}, {}
    stc = Stream(seed, "controls")
    ok_a = ok_c = ok_d = True
    for _ in range(N_CONTROL):
        A, SE, parts = draw_system(stc)
        n = len(A)
        whole = measures(A, SE, [list(range(n))])
        ok_a &= abs(whole["phistar"]) <= TOL
        S = steady(A, SE)
        res = add(add(S, mul(mul(A, S), tr(A)), -1.0), SE, -1.0)
        ok_c &= max(abs(x) for r in res for x in r) < 1e-10
        Sx, C, _ = system(A, SE)
        f = istar_fn(Sx, C, parts)
        beta, best = maximise(f)
        top = 4 * max(beta, 1e-3)
        ok_d &= all(f(top * j / 400) <= best + 1e-12 for j in range(401))
    ctl["(a) matched decoding gives I"] = ok_a
    ok_b = True
    for a in (0.3, 0.7, -0.5):
        S, C, Sp = system([[a]], [[1.0]])
        f = istar_fn(S, C, [[0]])
        s = 1 / (1 - a * a)
        for beta in (0.0, 0.5, 1.0, 2.0):
            Q = 1 / s + beta * a * a
            want = 0.5 * s * (beta - beta * beta * a * a / Q) + 0.5 * math.log(Q * s) - beta / 2
            ok_b &= abs(f(beta) - want) < 1e-12
        ok_b &= abs(f(1.0) - (-0.5 * math.log(1 - a * a))) < 1e-12 and abs(mutual_info(S, Sp) + 0.5 * math.log(1 - a * a)) < 1e-12
    ctl["(b) one unit by hand"] = ok_b
    ctl["(c) the steady state"] = ok_c
    ctl["(d) the search"] = ok_d
    a0 = [model[(0.0, k / 100)] for k in range(100)]
    rising = all(a0[k + 1]["phi_H"] > a0[k]["phi_H"] for k in range(99))
    ok_e = all(abs(m["phi_I"]) <= TOL for m in a0) and rising and model[(0.4, 0.99)]["phi_I"] < 0
    ctl["(e) the paper's Figure 3"] = ok_e
    met = sum(cond.values())
    m04 = [model[(0.4, c)]["phistar"] for c in (0.0, 0.5, 0.9)]
    out = {
        "systems": 200 + N_RANDOM + N_INDEP, "violations_lower": viol_lo, "violations_upper": viol_hi,
        "zero_cases_max": float(f"{zero_gap:.3g}"),
        "ratio_range": (f"Phi*/I over the drawn systems from {min(ratios):.6f} to {max(ratios):.6f}" if ratios else "n/a"),
        "model_a04": "Phi* at a = 0.4, c = 0, 0.5, 0.9: " + ", ".join(f"{x:.6f}" for x in m04),
        "phi_H_a0_c09": round(model[(0.0, 0.9)]["phi_H"], 6), "phi_I_a04_c099": round(model[(0.4, 0.99)]["phi_I"], 6),
        "conditions_met": met, "conditions_total": len(cond), "test_passed": int(met == len(cond)),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    detail = {"test": TEST, "conditions": cond, "controls": ctl,
              "model": {f"{a}/{c}": v for (a, c), v in model.items()}, "ratios_min_max": [min(ratios), max(ratios)]}
    return out, detail


def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    out, detail = assess(seed)
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
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
        sys.exit(f"phistar: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
