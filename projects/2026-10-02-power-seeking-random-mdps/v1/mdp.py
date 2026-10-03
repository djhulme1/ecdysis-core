"""Exact optimal values for deterministic MDPs with state rewards, vectorised over reward samples.

V*(s) = R(s) + gamma * max_{s' in succ(s)} V*(s').  Solved by batched policy iteration:
each policy is evaluated exactly with a linear solve, so there is no value-iteration truncation error.
"""
import numpy as np


def pad_succ(succ):
    """List of successor lists -> (n, d) int array, padded by repeating the first successor."""
    d = max(len(x) for x in succ)
    return np.array([list(x) + [x[0]] * (d - len(x)) for x in succ], dtype=np.int64)


def optimal_values(S, R, gamma, max_iter=200):
    """S: (n, d) successor array. R: (M, n) rewards. Returns V: (M, n) optimal values."""
    M, n = R.shape
    eye = np.eye(n)
    # greedy initial policy on immediate successor reward
    choice = np.argmax(R[:, S], axis=2)
    rows = np.arange(n)
    V = np.empty((M, n))
    active = np.arange(M)  # samples whose policy changed in the last sweep
    for it in range(max_iter):
        c = choice[active]
        m = len(active)
        nxt = S[rows[None, :], c]
        P = np.zeros((m, n, n))
        P[np.arange(m)[:, None], rows[None, :], nxt] = 1.0
        V[active] = np.linalg.solve(eye[None] - gamma * P, R[active][..., None])[..., 0]
        Q = V[active][:, S]  # (m, n, d)
        best = Q.max(axis=2)
        cur = np.take_along_axis(Q, c[..., None], axis=2)[..., 0]
        improve = best > cur + 1e-12
        changed = improve.any(axis=1)
        if not changed.any():
            return V
        choice[active] = np.where(improve, np.argmax(Q, axis=2), c)
        active = active[changed]
    raise RuntimeError("policy iteration did not converge")


def reach_count(succ, start):
    seen = {start}
    stack = [start]
    while stack:
        u = stack.pop()
        for v in succ[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen)


def start_stats(succ, gamma, R):
    """Statistics at state 0, which must have exactly two distinct successors."""
    S = pad_succ(succ)
    V = optimal_values(S, R, gamma)
    s1, s2 = succ[0]
    diff = V[:, s1] - V[:, s2]
    ties = int(np.sum(np.abs(diff) < 1e-12))
    p1 = float(np.mean(diff > 0))
    k = (1 - gamma) / gamma
    pw1 = k * (V[:, s1] - R[:, s1])
    pw2 = k * (V[:, s2] - R[:, s2])
    d = pw1 - pw2
    M = R.shape[0]
    return dict(
        p_opt_a1=p1,
        ties=ties,
        power1=float(pw1.mean()),
        power2=float(pw2.mean()),
        power_diff=float(d.mean()),
        power_diff_se=float(d.std(ddof=1) / np.sqrt(M)),
        reach1=reach_count(succ, s1),
        reach2=reach_count(succ, s2),
    )
