"""Fetch the published Yin-Yang split at a pinned commit (Kriener et al., arXiv:2102.08211)."""
import os, subprocess, numpy as np
REPO = "https://github.com/lkriener/yin_yang_data_set"
COMMIT = "e6eef9617b1dbd30d1f01508d462275747ae45b1"
HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, "data", "yin_yang_data_set")

def load():
    if not os.path.isdir(DST):
        os.makedirs(os.path.dirname(DST), exist_ok=True)
        subprocess.run(["git", "clone", "-q", REPO, DST], check=True)
        subprocess.run(["git", "-C", DST, "checkout", "-q", COMMIT], check=True)
    head = subprocess.run(["git", "-C", DST, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert head == COMMIT, head
    out = {}
    for s in ("train", "validation", "test"):
        x = np.load(os.path.join(DST, "publication_data", f"{s}_samples.npy")).astype(np.float32)
        y = np.load(os.path.join(DST, "publication_data", f"{s}_labels.npy")).astype(np.int64)
        out[s] = (x, y)
    return out
