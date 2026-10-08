#!/usr/bin/env python3
"""Spike counts against spike timing on the Spiking Heidelberg Digits, from the released data.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:a2cc7abd02eaa7ae) is from Cramer, Stradmann,
Schemmel and Zenke, "The Heidelberg Spiking Data Sets for the Systematic Evaluation of Spiking Neural Networks", IEEE
Transactions on Neural Networks and Learning Systems 33(7) (2022), arXiv:1910.07407: "By training a range of
conventional and spiking classifiers, we show that leveraging spike timing information within these datasets is
essential for good classification accuracy."

Its registered test: refuted if, on the Spiking Heidelberg Digits as released (the paper's train and test sets), the
paper's CNN, trained on spikes binned at 10 ms and into 64 channel groups as its appendix specifies, beats the best of
its spike-count SVMs (linear, polynomial of degree 2 or 3, RBF, on standardised per-channel counts with no timing) on
the test set by less than 16 points, half the gap the paper reports (92.4% against 60.0%); or if a classifier given
only the counts reaches 71.4%, the test accuracy of its recurrent spiking network.

The inputs are the two files the authors released, shd_train.h5.gz and shd_test.h5.gz (zenkelab.org, CC BY 4.0),
checked against their SHA-256 and read with h5py as data (nothing in them is run). Every rule below was fixed before
any seed existed. The seed (ECDYSIS_SEED) draws the validation split, the CNN's initial weights, the order of its
batches and its dropout masks, and the random states of the MLP and the boosted trees; nothing else.

1. The data. The training file must hold 8,156 digits and the test file 2,264, each with spikes/times, spikes/units
   and labels, every digit's times and units of one length, units 0 to 699, times finite and at or after 0, labels 0
   to 19; anything else is refused.
2. The counts, with no timing: for each digit, the number of spikes each of the 700 channels emitted, all of them,
   standardised by the mean and standard deviation of the training set (scikit-learn's StandardScaler), as the
   appendix's "Support vector machines" describes.
3. The paper's four SVMs: scikit-learn's SVC with the defaults of 2019 where the paper names none (C 1, gamma "auto",
   that is 1/700, coefficient 0, one against one; with no silent channel, today's default gamma "scale" is the same
   number), kernel linear, polynomial of degree 2, polynomial of degree 3 and RBF, each fitted to the whole training
   set and scored once on the test set.
4. Other classifiers given only the counts, for the 71.4% bar, a list fixed here: an RBF SVM over C in {1, 10, 100}
   and gamma in {1/3, 1, 3} x 1/700, on the standardised counts and, separately, on the standardised log(1 + count);
   multinomial logistic regression, C in {0.01, 0.1, 1}; k nearest neighbours, k in {1, 5, 15, 45}; a one-layer
   perceptron of 256 rectified units (scikit-learn's MLPClassifier, early stopping), alpha in {1e-4, 1e-2, 1}; all on
   the standardised counts; and histogram gradient boosting on the raw counts (300 iterations at most, early
   stopping). Each setting is chosen by accuracy on the validation tenth (rule 5) after fitting on the other nine
   tenths, the first best in the order listed; the chosen setting is refitted on the whole training set and scored
   once on the test set. The boosted trees have one setting and are fitted on the whole training set directly.
5. The validation tenth: 816 digits of the training set (round(8156 / 10)), drawn by the seed; the test set is never
   used to choose anything.
6. The CNN of the appendix's "Convolutional neural networks", written here in numpy, with Keras 2.3's defaults where
   the paper is silent. The input: the spikes before 1 s (the release's last spikes come at 1.37 s; the share left
   out is reported), counted in 100 bins of 10 ms by 64 channel groups (channel c in group floor(64 c / 700)), as raw
   counts, time along the first axis. The network: a 2-D convolution of 32 filters of 11 x 11 and ReLU; three blocks,
   each of two convolutions of 32 filters of 3 x 3, each followed by batch normalisation (momentum 0.99, epsilon
   0.001) and ReLU, then max-pooling of 2 x 2 and dropout at rate 0.2; flattening (7 x 3 x 32 = 672); a dense layer
   of 128 ReLU units; a softmax readout of 20. Valid padding and stride 1; Glorot-uniform weights, zero biases;
   categorical cross-entropy; Adamax (learning rate 0.002, beta 0.9 and 0.999, epsilon 1e-7, with Keras 2.3's bias
   correction of the first moment); batches of 32 in a new seeded order each epoch; float32. It is trained on the
   other nine tenths of the training set for 16 epochs, and the weights kept are those after the epoch with the
   best validation accuracy (the first such epoch); they are scored once on the test set.

test_passed is 1 if the CNN's test accuracy exceeds the best of rule 3's four by at least 16 points (at least 363 more
test digits right) and no classifier of rules 3 and 4 is right on 71.4% of the test digits (1,617 of 2,264) or more;
else 0.

What it cannot check: the paper's own runs (its 92.4% and 60.0% are means over repeated runs it does not list, and it
does not say how many epochs its CNN was trained for); the Spiking Speech Commands, which the test leaves out; the
LSTMs and the spiking networks themselves; and any count-only classifier beyond rule 4's list.

Writes results/outputs.json (19 values: the test accuracies in per cent, the margin in points, the CNN's epoch,
validation and fitting accuracy, the spikes left out and test_passed) and results/detail.json. Run with:
python3 snn/shd.py (about 90 minutes on two cores; "--trial" runs a small slice for the mechanics and is never a
receipt).
"""

import gzip
import hashlib
import io
import json
import os
import re
import sys
import time

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

INPUTS = (("shd_train.h5.gz", "e95bdc00c03c36537ff587d85d14efeee14a01b3846e14a70defc7e8a14e387c", 8156),
          ("shd_test.h5.gz", "bfd3d30d08a1eab1e9549f1b7f08d36044f38efa260f32241bafdf6e42bd2326", 2264))
N_CH, N_CLASSES = 700, 20
N_BINS, N_GROUPS = 100, 64                  # 10 ms bins over the first second; 64 channel groups
N_VALID = 816                               # round(8156 / 10)
EPOCHS = 16
BATCH = 32
RATE = 0.2                                  # dropout
MARGIN_PCT, BAR_PERMIL = 16, 714            # the test: 16 points; 71.4%
PAPER = {"svm_linear": 56.0, "svm_poly2": 48.3, "svm_poly3": 46.7, "svm_rbf": 60.0, "cnn": 92.4, "rsnn": 71.4}
F32 = np.float32


class Refused(Exception):
    """An input that is not what the rules say it must be."""


# --- the seed ---------------------------------------------------------------------------------------------------------

def stream(seed, label):
    """A generator for one use of the seed: SHA-256 of the seed, a bar and the use's label."""
    h = hashlib.sha256(f"{seed}|{label}".encode("ascii")).digest()
    return np.random.default_rng(int.from_bytes(h[:16], "big"))


def state32(seed, label):
    """A 32-bit random state for scikit-learn, from the seed and a label."""
    return int.from_bytes(hashlib.sha256(f"{seed}|{label}".encode("ascii")).digest()[:4], "big")


# --- rule 1: the data -------------------------------------------------------------------------------------------------

def check_digits(times, units, labels, n):
    if not (len(times) == len(units) == len(labels) == n):
        raise Refused(f"{len(times)}, {len(units)} and {len(labels)} digits, not {n}")
    labels = np.asarray(labels)
    if labels.dtype.kind not in "iu" or labels.min() < 0 or labels.max() >= N_CLASSES:
        raise Refused("labels outside 0 to 19")
    for i, (t, u) in enumerate(zip(times, units)):
        if len(t) != len(u):
            raise Refused(f"digit {i}: {len(t)} times and {len(u)} units")
        if np.asarray(u).dtype.kind not in "iu" or (len(u) and int(np.max(u)) >= N_CH):
            raise Refused(f"digit {i}: a unit outside 0 to 699")
        t64 = np.asarray(t, dtype=np.float64)
        if len(t64) and (not np.all(np.isfinite(t64)) or t64.min() < 0):
            raise Refused(f"digit {i}: a time that is negative or not finite")
    return list(times), list(units), labels.astype(np.int64)


def read(inputs, name, sha, n):
    path = os.path.join(inputs, name)
    with open(path, "rb") as fh:
        raw = fh.read()
    if hashlib.sha256(raw).hexdigest() != sha:
        sys.exit(f"{name}: its SHA-256 is not the release's")
    import h5py
    with h5py.File(io.BytesIO(gzip.decompress(raw)), "r") as f:
        for key in ("spikes/times", "spikes/units", "labels"):
            if key not in f:
                raise Refused(f"{name}: no {key}")
        return check_digits(f["spikes/times"][:], f["spikes/units"][:], f["labels"][:], n)


# --- rules 2 and 6: the features --------------------------------------------------------------------------------------

def counts(units):
    """Rule 2: the spikes of each channel, all of them, one row per digit."""
    return np.stack([np.bincount(np.asarray(u, dtype=np.int64), minlength=N_CH) for u in units]).astype(np.float64)


def binned(times, units):
    """Rule 6: (digits, 100 bins of 10 ms, 64 groups) of raw counts before 1 s; and the spikes left out, of all."""
    X = np.zeros((len(times), N_BINS, N_GROUPS), F32)
    left, total = 0, 0
    for i, (t, u) in enumerate(zip(times, units)):
        b = np.floor(np.asarray(t, dtype=np.float64) * 100).astype(np.int64)   # exact: a float16 time times 100
        g = (np.asarray(u, dtype=np.int64) * N_GROUPS) // N_CH
        keep = b < N_BINS
        X[i] = np.bincount(b[keep] * N_GROUPS + g[keep], minlength=N_BINS * N_GROUPS).reshape(N_BINS, N_GROUPS)
        left += int((~keep).sum())
        total += len(b)
    return X, left, total


def split(seed, n=8156, n_valid=N_VALID):
    """Rule 5: (the nine tenths, the validation tenth), as sorted indices into the training set."""
    perm = stream(seed, "validation").permutation(n)
    return np.sort(perm[n_valid:]), np.sort(perm[:n_valid])


# --- rule 6: the CNN, in numpy ----------------------------------------------------------------------------------------

def conv_fwd(X, W, b):
    """A valid 2-D convolution, stride 1, X (B, H, W, C), W (kh, kw, C, F): Y (B, H', W', F) and the patches."""
    B, H, Wd, C = X.shape
    kh, kw, _, F = W.shape
    Ho, Wo = H - kh + 1, Wd - kw + 1
    if C == 1:
        cols = sliding_window_view(X[..., 0], (kh, kw), axis=(1, 2)).reshape(B * Ho * Wo, kh * kw)
    else:                                       # (B, H', W', C, kh, kw) -> (B, H', W', kh, kw, C), W's order
        cols = np.ascontiguousarray(sliding_window_view(X, (kh, kw), axis=(1, 2)).transpose(0, 1, 2, 4, 5, 3))
        cols = cols.reshape(B * Ho * Wo, kh * kw * C)
    Y = cols @ W.reshape(kh * kw * C, F)
    Y += b
    return Y.reshape(B, Ho, Wo, F), cols


def conv_bwd(dY, cols, x_shape, W, need_dx=True):
    B, H, Wd, C = x_shape
    kh, kw, _, F = W.shape
    Ho, Wo = dY.shape[1], dY.shape[2]
    dYm = dY.reshape(B * Ho * Wo, F)
    dW = (cols.T @ dYm).reshape(W.shape)
    db = dYm.sum(axis=0, dtype=np.float64).astype(dY.dtype)
    if not need_dx:
        return dW, db, None
    dcols = (dYm @ W.reshape(kh * kw * C, F).T).reshape(B, Ho, Wo, kh * kw, C)
    dX = np.zeros(x_shape, dY.dtype)
    for i in range(kh):
        for j in range(kw):
            dX[:, i:i + Ho, j:j + Wo, :] += dcols[:, :, :, i * kw + j, :]
    return dW, db, dX


def bn_train(x, g, be, mm, mv, momentum=0.99, eps=1e-3):
    """Batch normalisation on the batch's statistics; the moving mean and variance (unbiased) updated in place."""
    C = x.shape[-1]
    xm = x.reshape(-1, C)
    m = xm.shape[0]
    mu = xm.mean(axis=0, dtype=np.float64)
    var = np.square(xm - mu.astype(x.dtype)).mean(axis=0, dtype=np.float64)
    inv = (1.0 / np.sqrt(var + eps)).astype(x.dtype)
    xhat = (xm - mu.astype(x.dtype)) * inv
    y = xhat * g + be
    mm *= momentum
    mm += ((1 - momentum) * mu).astype(mm.dtype)
    mv *= momentum
    mv += ((1 - momentum) * var * m / max(m - 1, 1)).astype(mv.dtype)
    return y.reshape(x.shape), (xhat, inv)


def bn_infer(x, g, be, mm, mv, eps=1e-3):
    return (x - mm) * (g / np.sqrt(mv + eps)).astype(x.dtype) + be


def bn_bwd(dy, cache, g):
    xhat, inv = cache
    C = dy.shape[-1]
    dym = dy.reshape(-1, C)
    m = dy.dtype.type(dym.shape[0])             # typed: a bare int over 65535 would make the arithmetic float64
    dbe = dym.sum(axis=0, dtype=np.float64).astype(dy.dtype)
    dg = (dym * xhat).sum(axis=0, dtype=np.float64).astype(dy.dtype)
    dx = (g * inv / m) * (m * dym - dbe - xhat * dg)
    return dx.reshape(dy.shape), dg, dbe


def pool_fwd(x):
    """Max-pooling of 2 x 2, stride 2, valid (an odd last row or column is dropped)."""
    B, H, W, C = x.shape
    H2, W2 = H // 2, W // 2
    xc = x[:, :2 * H2, :2 * W2, :].reshape(B, H2, 2, W2, 2, C).transpose(0, 1, 3, 5, 2, 4).reshape(B, H2, W2, C, 4)
    idx = xc.argmax(axis=-1)
    return np.take_along_axis(xc, idx[..., None], axis=-1)[..., 0], idx


def pool_bwd(dy, idx, x_shape):
    B, H, W, C = x_shape
    H2, W2 = H // 2, W // 2
    d = np.zeros((B, H2, W2, C, 4), dy.dtype)
    np.put_along_axis(d, idx[..., None], dy[..., None], axis=-1)
    dx = np.zeros(x_shape, dy.dtype)
    dx[:, :2 * H2, :2 * W2, :] = d.reshape(B, H2, W2, C, 2, 2).transpose(0, 1, 4, 2, 5, 3).reshape(B, 2 * H2, 2 * W2, C)
    return dx


def softmax_ce(logits, y):
    """Categorical cross-entropy of the softmax, the batch's mean, with its gradient by the logits."""
    z = logits - logits.max(axis=1, keepdims=True)
    e = np.exp(z)
    p = e / e.sum(axis=1, keepdims=True)
    rows = np.arange(len(y))
    loss = float(-np.log(np.clip(p[rows, y].astype(np.float64), 1e-7, 1.0)).mean())
    d = p.copy()
    d[rows, y] -= 1
    d /= len(y)
    return loss, d


BLOCKS = ("b1", "b2", "b3")


def out_shape(in_shape):
    h, w = in_shape[0] - 10, in_shape[1] - 10
    for _ in BLOCKS:
        h, w = (h - 4) // 2, (w - 4) // 2
    if h < 1 or w < 1:
        raise ValueError(f"input {in_shape} is too small for the network")
    return h, w


def glorot(rng, shape, fan_in, fan_out):
    lim = np.sqrt(6.0 / (fan_in + fan_out))
    return rng.uniform(-lim, lim, shape).astype(F32)


def init(rng, in_shape=(N_BINS, N_GROUPS)):
    """Rule 6's parameters (Glorot-uniform weights, zero biases, BN scales 1 and shifts 0) and BN's moving state."""
    P, S = {}, {}
    P["c1.W"], P["c1.b"] = glorot(rng, (11, 11, 1, 32), 121, 121 * 32), np.zeros(32, F32)
    for k in BLOCKS:
        for s in "ab":
            n = k + s
            P[n + ".W"], P[n + ".b"] = glorot(rng, (3, 3, 32, 32), 288, 288), np.zeros(32, F32)
            P[n + ".g"], P[n + ".be"] = np.ones(32, F32), np.zeros(32, F32)
            S[n + ".mm"], S[n + ".mv"] = np.zeros(32, F32), np.ones(32, F32)
    h, w = out_shape(in_shape)
    P["d.W"], P["d.b"] = glorot(rng, (h * w * 32, 128), h * w * 32, 128), np.zeros(128, F32)
    P["o.W"], P["o.b"] = glorot(rng, (128, N_CLASSES), 128, N_CLASSES), np.zeros(N_CLASSES, F32)
    return P, S


def forward(P, S, X, train, drop_rng=None):
    """Logits for X (B, H, W, 1); in training, batch statistics (moving state updated) and dropout."""
    caches = {}
    z, c = conv_fwd(X, P["c1.W"], P["c1.b"])
    h = np.maximum(z, 0)
    caches["c1"] = (c, X.shape, h)
    for k in BLOCKS:
        for s in "ab":
            n = k + s
            xs = h.shape
            z, c = conv_fwd(h, P[n + ".W"], P[n + ".b"])
            if train:
                z, bc = bn_train(z, P[n + ".g"], P[n + ".be"], S[n + ".mm"], S[n + ".mv"])
            else:
                z, bc = bn_infer(z, P[n + ".g"], P[n + ".be"], S[n + ".mm"], S[n + ".mv"]), None
            h = np.maximum(z, 0)
            caches[n] = (c if train else None, xs, bc, h if train else None)
        ps = h.shape
        h, idx = pool_fwd(h)
        mask = None
        if train:
            mask = (drop_rng.random(h.shape, dtype=F32) >= RATE).astype(h.dtype) / h.dtype.type(1 - RATE)
            h = h * mask
        caches[k] = (ps, idx if train else None, mask)
    fs = h.shape
    f = h.reshape(len(X), -1)
    a = np.maximum(f @ P["d.W"] + P["d.b"], 0)
    caches["head"] = (fs, f, a)
    return a @ P["o.W"] + P["o.b"], caches


def backward(P, caches, dlogits):
    G = {}
    fs, f, a = caches["head"]
    G["o.W"], G["o.b"] = a.T @ dlogits, dlogits.sum(axis=0)
    dz = (dlogits @ P["o.W"].T) * (a > 0)
    G["d.W"], G["d.b"] = f.T @ dz, dz.sum(axis=0)
    dh = (dz @ P["d.W"].T).reshape(fs)
    for k in reversed(BLOCKS):
        ps, idx, mask = caches[k]
        dh = pool_bwd(dh * mask, idx, ps)
        for s in "ba":
            n = k + s
            c, xs, bc, h = caches[n]
            dz, G[n + ".g"], G[n + ".be"] = bn_bwd(dh * (h > 0), bc, P[n + ".g"])
            G[n + ".W"], G[n + ".b"], dh = conv_bwd(dz, c, xs, P[n + ".W"])
    c, xs, h = caches["c1"]
    G["c1.W"], G["c1.b"], _ = conv_bwd(dh * (h > 0), c, xs, P["c1.W"], need_dx=False)
    return G


class Adamax:
    """Keras 2.3's Adamax: lr_t = lr / (1 - beta_1^t); m = b1 m + (1 - b1) g; u = max(b2 u, |g|); p -= lr_t m / (u + eps)."""

    def __init__(self, P, lr=0.002, b1=0.9, b2=0.999, eps=1e-7):
        self.lr, self.b1, self.b2, self.eps, self.t = lr, b1, b2, eps, 0
        self.m = {k: np.zeros_like(v) for k, v in P.items()}
        self.u = {k: np.zeros_like(v) for k, v in P.items()}

    def step(self, P, G):
        self.t += 1
        lr_t = self.lr / (1 - self.b1 ** self.t)
        for k, p in P.items():
            g = G[k].astype(p.dtype, copy=False)
            m, u = self.m[k], self.u[k]
            m *= self.b1
            m += (1 - self.b1) * g
            np.maximum(self.b2 * u, np.abs(g), out=u)
            p -= (lr_t * m / (u + self.eps)).astype(p.dtype, copy=False)


def predict(P, S, X, batch=64):
    out = []
    for i in range(0, len(X), batch):
        logits, _ = forward(P, S, X[i:i + batch, ..., None], train=False)
        out.append(logits.argmax(axis=1))
    return np.concatenate(out)


def train_cnn(seed, Xfit, yfit, Xval, yval, epochs=EPOCHS, log=print):
    """Rule 6: train, keep the weights after the epoch with the best validation accuracy (the first such)."""
    P, S = init(stream(seed, "cnn-init"), Xfit.shape[1:3])
    opt = Adamax(P)
    order, drops = stream(seed, "cnn-order"), stream(seed, "cnn-dropout")
    best, curve = None, []
    for ep in range(1, epochs + 1):
        t0, losses, right = time.time(), [], 0
        perm = order.permutation(len(Xfit))
        for i in range(0, len(perm), BATCH):
            bi = perm[i:i + BATCH]
            logits, caches = forward(P, S, Xfit[bi][..., None], True, drops)
            loss, d = softmax_ce(logits, yfit[bi])
            losses.append(loss * len(bi))
            right += int((logits.argmax(axis=1) == yfit[bi]).sum())
            opt.step(P, backward(P, caches, d.astype(F32)))
        val_right = int((predict(P, S, Xval) == yval).sum())
        curve.append({"epoch": ep, "loss": round(sum(losses) / len(Xfit), 5), "train_right": right,
                      "val_right": val_right, "seconds": round(time.time() - t0, 1)})
        log(f"shd: epoch {ep}: loss {curve[-1]['loss']}, train {right}/{len(Xfit)} (dropout on), "
            f"validation {val_right}/{len(Xval)}, {curve[-1]['seconds']} s")
        if best is None or val_right > best[0]:
            best = (val_right, ep, {k: v.copy() for k, v in P.items()}, {k: v.copy() for k, v in S.items()})
    return best, curve


# --- rules 3 and 4: the classifiers given only the counts --------------------------------------------------------------

PAPER_SVMS = (("svm_linear", {"kernel": "linear"}), ("svm_poly2", {"kernel": "poly", "degree": 2}),
              ("svm_poly3", {"kernel": "poly", "degree": 3}), ("svm_rbf", {"kernel": "rbf"}))
GRID = tuple((C, g) for C in (1, 10, 100) for g in (1 / 3, 1, 3))


def scaled(fit_rows, *others, log1p=False):
    """Standardised by the rows fitted (scikit-learn's StandardScaler), optionally of log(1 + count)."""
    from sklearn.preprocessing import StandardScaler
    f = np.log1p if log1p else (lambda a: a)
    sc = StandardScaler().fit(f(fit_rows))
    return [sc.transform(f(a)) for a in (fit_rows,) + others]


def paper_svm(kw):
    from sklearn.svm import SVC
    return SVC(C=1.0, gamma="auto", coef0=0.0, cache_size=500, **kw)


def extras(seed):
    """Rule 4's list, in order: (name, log(1 + count)?, settings, the classifier for a setting)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.svm import SVC

    def rbf(s):
        return SVC(C=s[0], gamma=s[1] / N_CH, cache_size=500)

    def mlp(a):
        return MLPClassifier(hidden_layer_sizes=(256,), alpha=a, early_stopping=True, max_iter=300,
                             random_state=state32(seed, "mlp"))
    return (("svm_rbf_grid", False, GRID, rbf), ("svm_rbf_log_grid", True, GRID, rbf),
            ("logreg", False, (0.01, 0.1, 1.0), lambda C: LogisticRegression(C=C, max_iter=5000)),
            ("knn", False, (1, 5, 15, 45), lambda k: KNeighborsClassifier(n_neighbors=k)),
            ("mlp", False, (1e-4, 1e-2, 1.0), mlp))


def right(clf, Z, y):
    return int((clf.predict(Z) == y).sum())


def count_classifiers(seed, Ctr, ytr, Cte, yte, fit, val, log=print):
    """Rules 3 and 4: {name: {test_right, ...}} for the four SVMs and the others."""
    out = {}
    Ztr, Zte = scaled(Ctr, Cte)
    for name, kw in PAPER_SVMS:
        t0 = time.time()
        clf = paper_svm(kw).fit(Ztr, ytr)
        out[name] = {"test_right": right(clf, Zte, yte), "train_right": right(clf, Ztr, ytr),
                     "support": int(clf.n_support_.sum()), "seconds": round(time.time() - t0, 1)}
        log(f"shd: {name}: test {out[name]['test_right']}/{len(yte)}, {out[name]['seconds']} s")
    for name, log1p, settings, make in extras(seed):
        t0 = time.time()
        Zf, Zv = scaled(Ctr[fit], Ctr[val], log1p=log1p)
        scores = [right(make(s).fit(Zf, ytr[fit]), Zv, ytr[val]) for s in settings]
        chosen = settings[int(np.argmax(scores))]                    # the first best, in the order listed
        Za, Zt = scaled(Ctr, Cte, log1p=log1p)
        clf = make(chosen).fit(Za, ytr)
        out[name] = {"test_right": right(clf, Zt, yte), "chosen": chosen, "validation_right": scores,
                     "settings": list(settings), "seconds": round(time.time() - t0, 1)}
        log(f"shd: {name}: chose {chosen} (validation {max(scores)}/{len(val)}), test {out[name]['test_right']}"
            f"/{len(yte)}, {out[name]['seconds']} s")
    from sklearn.ensemble import HistGradientBoostingClassifier
    t0 = time.time()
    clf = HistGradientBoostingClassifier(max_iter=300, early_stopping=True,
                                         random_state=state32(seed, "hgb")).fit(Ctr, ytr)
    out["hgb"] = {"test_right": right(clf, Cte, yte), "iterations": int(clf.n_iter_), "seconds": round(time.time() - t0, 1)}
    log(f"shd: hgb: {out['hgb']['iterations']} iterations, test {out['hgb']['test_right']}/{len(yte)}, "
        f"{out['hgb']['seconds']} s")
    return out


# --- the verdict ------------------------------------------------------------------------------------------------------

def verdict(svm_right, count_right, cnn_right, n):
    """1 if the CNN is right on at least 16 points more of the test digits than the best of the four SVMs and no
    count-only classifier is right on 71.4% of them or more; else 0. Counts of digits right, compared exactly."""
    best_svm = max(svm_right.values())
    margin_ok = 100 * (cnn_right - best_svm) >= MARGIN_PCT * n
    bar_ok = 1000 * max(count_right.values()) < BAR_PERMIL * n
    return int(margin_ok and bar_ok), {"margin": bool(margin_ok), "bar": bool(bar_ok)}


def pct(k, n):
    return round(100.0 * k / n, 2)


def run(seed, inputs="inputs", results="results", log=print, trial=False):
    t_start = time.time()
    (tr_t, tr_u, ytr), (te_t, te_u, yte) = [read(inputs, name, sha, n) for name, sha, n in INPUTS]
    Ctr, Cte = counts(tr_u), counts(te_u)
    Xtr, left_tr, total_tr = binned(tr_t, tr_u)
    Xte, left_te, total_te = binned(te_t, te_u)
    del tr_t, tr_u, te_t, te_u
    fit, val = split(seed)
    epochs = EPOCHS
    if trial:                       # mechanics only: a small slice, one epoch; never what a receipt runs
        fit, val, keep = fit[:600], val[:200], np.arange(400)
        Cte, Xte, yte = Cte[keep], Xte[keep], yte[keep]
        sub = np.sort(np.concatenate([fit, val]))
        Ctr = Ctr[sub]
        ytr_full = ytr
        remap = {int(j): i for i, j in enumerate(sub)}
        fit_s, val_s = np.array([remap[int(j)] for j in fit]), np.array([remap[int(j)] for j in val])
        ytr = ytr_full[sub]
        Xtr = Xtr[sub]
        fit, val, epochs = fit_s, val_s, 1
    n = len(yte)
    log(f"shd: read and binned in {time.time() - t_start:.0f} s; spikes at or after 1 s: {left_tr + left_te} of "
        f"{total_tr + total_te}")
    cc = count_classifiers(seed, Ctr, ytr, Cte, yte, fit, val, log)
    del Ctr, Cte
    best, curve = train_cnn(seed, Xtr[fit], ytr[fit], Xtr[val], ytr[val], epochs=epochs, log=log)
    val_right, epoch, P, S = best
    cnn_right = int((predict(P, S, Xte) == yte).sum())
    cnn_fit_right = int((predict(P, S, Xtr[fit]) == ytr[fit]).sum())
    svm_right = {k: cc[k]["test_right"] for k, _ in PAPER_SVMS}
    count_right = {k: v["test_right"] for k, v in cc.items()}
    passed, conditions = verdict(svm_right, count_right, cnn_right, n)
    best_svm = max(svm_right.values())
    best_count_name = max(count_right, key=lambda k: (count_right[k], -list(count_right).index(k)))
    out = {k: pct(v, n) for k, v in svm_right.items()}
    out.update({
        "svm_best": pct(best_svm, n),
        "cnn": pct(cnn_right, n),
        "margin": round(100.0 * (cnn_right - best_svm) / n, 2),
        "count_best": pct(count_right[best_count_name], n),
        "cnn_epoch": epoch,
        "cnn_validation": pct(val_right, len(val)),
        "cnn_fit": pct(cnn_fit_right, len(fit)),
        "spikes_left_out": left_tr + left_te,
        "test_passed": passed,
    })
    out.update({k: pct(cc[k]["test_right"], n) for k in ("svm_rbf_grid", "svm_rbf_log_grid", "logreg", "knn", "mlp",
                                                           "hgb")})
    detail = {"inputs": [{"name": nm, "sha256": sh, "digits": d} for nm, sh, d in INPUTS],
              "test_digits": n, "fit_digits": len(fit), "validation_digits": len(val),
              "spikes": {"train_total": total_tr, "train_left_out": left_tr, "test_total": total_te,
                         "test_left_out": left_te},
              "count_classifiers": cc, "count_best": best_count_name,
              "cnn": {"epochs": epochs, "chosen_epoch": epoch, "validation_right": val_right, "test_right": cnn_right,
                      "fit_right": cnn_fit_right, "curve": curve},
              "conditions": conditions, "paper": PAPER, "trial": bool(trial),
              "seconds": round(time.time() - t_start, 1)}
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
    trial = sys.argv[1:] == ["--trial"]
    try:
        out, _ = run(seed, results="results-trial" if trial else "results",
                     log=lambda m: print(m, file=sys.stderr, flush=True), trial=trial)
    except Refused as e:
        sys.exit(f"shd: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
