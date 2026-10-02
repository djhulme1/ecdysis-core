"""Arm A: ANN baselines of Kriener et al. (arXiv:2102.08211), 20 seeds, vectorised across seeds.
Each seed has its own nn.Linear-default initialisation (torch.manual_seed(seed)), its own
per-epoch shuffle, and its own Adam state (Adam is elementwise and the summed loss decouples seeds).
Adam lr 0.01, batch 20, 300 epochs, ReLU, cross-entropy. Outputs results/arm_a.csv."""
import os, sys, time, csv, numpy as np, torch
from data import load
torch.set_num_threads(1)
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = list(range(20)); EPOCHS = int(os.environ.get("EPOCHS", 300)); BS = 20; LR = 0.01
CONFIGS = [("shallow", 0, False), ("deep", 10, False), ("deep", 20, False), ("deep", 30, False),
           ("frozen", 20, True), ("frozen", 30, True)]

def init(seed, hidden):
    torch.manual_seed(seed)
    if hidden == 0:
        l = torch.nn.Linear(4, 3); return [l.weight.T.detach().clone(), l.bias.detach().clone()]
    l1 = torch.nn.Linear(4, hidden); l2 = torch.nn.Linear(hidden, 3)
    return [l1.weight.T.detach().clone(), l1.bias.detach().clone(), l2.weight.T.detach().clone(), l2.bias.detach().clone()]

def forward(p, x):  # x: [S, B, 4]
    if len(p) == 2:
        return torch.baddbmm(p[1][:, None, :], x, p[0])
    h = torch.relu(torch.baddbmm(p[1][:, None, :], x, p[0]))
    return torch.baddbmm(p[3][:, None, :], h, p[2])

def acc(p, x, y):
    with torch.no_grad():
        S = p[0].shape[0]
        out = forward(p, x[None].expand(S, -1, -1))
        return (out.argmax(-1) == y[None]).float().mean(1).numpy()

def run(kind, hidden, frozen, d):
    xtr, ytr = map(torch.tensor, d["train"]); xva, yva = map(torch.tensor, d["validation"]); xte, yte = map(torch.tensor, d["test"])
    S = len(SEEDS); N = len(ytr)
    parts = [init(s, hidden) for s in SEEDS]
    p = [torch.stack([q[i] for q in parts]).requires_grad_(not (frozen and i < 2)) for i in range(len(parts[0]))]
    trainable = p[2:] if frozen else p
    opt = torch.optim.Adam(trainable, lr=LR)
    gens = [np.random.RandomState(1000 + s) for s in SEEDS]
    best_va = np.full(S, -1.0); te_at_best = np.zeros(S)
    for ep in range(EPOCHS):
        perms = torch.tensor(np.stack([g.permutation(N) for g in gens]))  # [S, N]
        for b in range(0, N, BS):
            idx = perms[:, b:b + BS]
            xb, yb = xtr[idx], ytr[idx]
            out = forward(p, xb)
            loss = torch.nn.functional.cross_entropy(out.reshape(-1, 3), yb.reshape(-1), reduction="none").view(S, -1).mean(1).sum()
            opt.zero_grad(); loss.backward(); opt.step()
        va = acc(p, xva, yva); te = acc(p, xte, yte)
        better = va > best_va; best_va[better] = va[better]; te_at_best[better] = te[better]
    final = acc(p, xte, yte)
    return final, te_at_best, best_va

if __name__ == "__main__":
    d = load(); os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    rows = []
    for kind, hidden, frozen in CONFIGS:
        t = time.time(); final, tb, bv = run(kind, hidden, frozen, d)
        for s, f, a, v in zip(SEEDS, final, tb, bv):
            rows.append(dict(config=kind, hidden=hidden, seed=s, test_final=round(float(f), 4), test_at_best_val=round(float(a), 4), best_val=round(float(v), 4)))
        print(f"{kind}{hidden}: final {final.mean()*100:.2f} +- {final.std(ddof=1)*100:.2f}  ({time.time()-t:.0f}s)", flush=True)
    with open(os.path.join(HERE, "results", "arm_a.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
