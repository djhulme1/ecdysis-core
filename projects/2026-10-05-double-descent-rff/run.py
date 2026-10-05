"""Double descent of random Fourier features on MNIST (Belkin, Hsu, Ma and Mandal, arXiv:1812.11118), re-run as the paper
describes (see PLAN.md).

A random Fourier features model h(x) = sum_k a_k phi(x; v_k), with v_k ~ N(0, sigma^-2 I), sigma = 5, is fitted by least squares
to a random subset of n = 10,000 MNIST training examples with one-hot targets for the ten classes (sum of squared losses), taking
the minimum-norm solution where the minimiser is not unique; the number of features N is swept through the interpolation
threshold N = n, and the test zero-one error and squared loss are recorded at each N on the 10,000 MNIST test examples. All
randomness (the subset, the features) comes from ECDYSIS_SEED; the clock is never read. Reads MNIST at inputs/ (inputs/0.1).
Writes results/outputs.json: numbers only. Dependencies: numpy (and scipy if present, for the eigendecomposition).
"""
import gzip
import json
import os
import struct
import sys
import time

import numpy as np

try:
    from scipy.linalg import eigh
except Exception:  # pragma: no cover
    eigh = np.linalg.eigh

N_TRAIN = int(os.environ.get("DD_N", "10000"))
SIGMA = 5.0
SWEEP = [int(x) for x in os.environ.get("DD_SWEEP", "100,500,1000,2000,3000,4000,5000,6000,7000,8000,9000,9500,9800,10000,10200,10500,11000,12000,15000,20000,30000,40000").split(",")]
BLOCK = 2000
RCOND = 1e-10


def idx(path):
    with gzip.open(path, "rb") as fh:
        magic, n = struct.unpack(">II", fh.read(8))
        dims = magic & 0xFF
        shape = [n] + [struct.unpack(">I", fh.read(4))[0] for _ in range(dims - 1)]
        return np.frombuffer(fh.read(), dtype=np.uint8).reshape(shape)


def load():
    xtr = idx("inputs/train-images-idx3-ubyte.gz").reshape(-1, 784).astype(np.float64) / 255.0
    ytr = idx("inputs/train-labels-idx1-ubyte.gz").astype(np.int64)
    xte = idx("inputs/t10k-images-idx3-ubyte.gz").reshape(-1, 784).astype(np.float64) / 255.0
    yte = idx("inputs/t10k-labels-idx1-ubyte.gz").astype(np.int64)
    return xtr, ytr, xte, yte


def features(x, v, b):
    """Real random Fourier features sqrt(2) cos(<v, x> + b): N real parameters, so the interpolation threshold is N = n."""
    return np.sqrt(2.0) * np.cos(x @ v + b)


def fit_predict(K, K_te, Y):
    """Minimum-norm least squares through the kernel of the features: predictions K_te K^+ Y, with K^+ the pseudo-inverse."""
    w, U = eigh(K)
    keep = w > RCOND * w.max()
    alpha = U[:, keep] @ ((U[:, keep].T @ Y) / w[keep][:, None])
    return K_te @ alpha, K @ alpha, int(keep.sum())


def main():
    seed_hex = os.environ["ECDYSIS_SEED"]
    if len(seed_hex) != 64:
        sys.exit("ECDYSIS_SEED must be 64 hex characters")
    rng = np.random.default_rng(int(seed_hex[:16], 16))
    xtr_all, ytr_all, xte, yte = load()
    sub = rng.permutation(len(ytr_all))[:N_TRAIN]
    xtr, ytr = xtr_all[sub], ytr_all[sub]
    n, d = xtr.shape
    Y = np.eye(10)[ytr]
    sweep = sorted(set(SWEEP))
    n_max = sweep[-1]
    K = np.zeros((n, n))
    K_te = np.zeros((len(yte), n))
    done = 0
    results = {}
    t0 = time.time()
    for N in sweep:
        while done < N:
            m = min(BLOCK, N - done)
            v = rng.normal(0.0, 1.0 / SIGMA, size=(d, m))
            b = rng.uniform(0.0, 2.0 * np.pi, size=(m,))
            ftr = features(xtr, v, b)
            fte = features(xte, v, b)
            K += ftr @ ftr.T
            K_te += fte @ ftr.T
            done += m
        pred_te, pred_tr, rank = fit_predict(K, K_te, Y)
        zo_te = float((pred_te.argmax(1) != yte).mean() * 100.0)
        zo_tr = float((pred_tr.argmax(1) != ytr).mean() * 100.0)
        sq_te = float(((pred_te - np.eye(10)[yte]) ** 2).sum(1).mean())
        results[N] = (zo_te, sq_te, zo_tr, rank)
        print(f"N {N:6d}: test zero-one {zo_te:6.2f}%  test squared {sq_te:8.4f}  train zero-one {zo_tr:6.2f}%  rank {rank}  ({time.time() - t0:.0f}s)", flush=True)
    below = [N for N in sweep if N < n]
    above = [N for N in sweep if N > n]
    zo = {N: r[0] for N, r in results.items()}
    sq = {N: r[1] for N, r in results.items()}
    argmax_zo = max(sweep, key=lambda N: zo[N])
    argmax_sq = max(sweep, key=lambda N: sq[N])
    out = {
        "n_train": n, "n_test": int(len(yte)), "n_max_features": n_max,
        "zo_at_1000": round(zo[1000], 3) if 1000 in zo else -1,
        "zo_min_below_n": round(min(zo[N] for N in below), 3),
        "zo_argmin_below_n": min(below, key=lambda N: zo[N]),
        "zo_at_n": round(zo[n], 3) if n in zo else -1,
        "zo_at_2n": round(zo[2 * n], 3) if 2 * n in zo else -1,
        "zo_at_max": round(zo[n_max], 3),
        "zo_argmax_N": argmax_zo,
        "sq_at_n": round(sq[n], 4) if n in sq else -1,
        "sq_at_max": round(sq[n_max], 4),
        "sq_argmax_N": argmax_sq,
        "train_zo_at_n": round(results[n][2], 3) if n in results else -1,
        "rank_at_n": results[n][3] if n in results else -1,
    }
    os.makedirs("results", exist_ok=True)
    with open("results/outputs.json", "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
