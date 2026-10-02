"""Arm B: surrogate-gradient LIF network on Yin-Yang, four surrogate shapes x four steepnesses x 5 seeds.
Tests Neftci, Mostafa & Zenke (arXiv:1901.09948): success "not crucially dependent on the details of the surrogate".
Seeds are vectorised (stacked weights, decoupled summed loss, elementwise Adam). Outputs results/arm_b.csv."""
import os, sys, time, csv, math, numpy as np, torch
from data import load
torch.set_num_threads(1)
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = list(range(5)); EPOCHS = int(os.environ.get("EPOCHS", 60)); BS = 100; LR = 2e-3
T = 40; NH = 120; A_M = math.exp(-1 / 10); A_S = math.exp(-1 / 5)
SHAPES = ["fast_sigmoid", "sigmoid", "triangle", "exponential"]; BETAS = [2, 5, 10, 25]

def surrogate(u, shape, beta):  # peak height 1 at u = 0
    if shape == "fast_sigmoid": return 1.0 / (beta * u.abs() + 1.0) ** 2
    if shape == "sigmoid":
        s = torch.sigmoid(beta * u); return 4.0 * s * (1.0 - s)
    if shape == "triangle": return torch.clamp(1.0 - beta * u.abs(), min=0.0)
    if shape == "exponential": return torch.exp(-beta * u.abs())
    raise ValueError(shape)

class Spike(torch.autograd.Function):
    @staticmethod
    def forward(ctx, u, shape, beta):
        ctx.save_for_backward(u); ctx.shape = shape; ctx.beta = beta
        return (u > 0).float()
    @staticmethod
    def backward(ctx, g):
        (u,) = ctx.saved_tensors
        return g * surrogate(u, ctx.shape, ctx.beta), None, None

def forward(p, x, shape, beta):  # x: [S, B, 4] -> logits [S, B, 3], mean hidden rate
    S, B, _ = x.shape
    xin = torch.cat([x, torch.ones(S, B, 1)], -1)
    drive = torch.bmm(xin, p[0])  # constant current per step
    i1 = torch.zeros(S, B, NH); v = torch.zeros(S, B, NH)
    i2 = torch.zeros(S, B, 3); u = torch.zeros(S, B, 3)
    umax = torch.full((S, B, 3), -1e9); nspk = 0.0
    for t in range(T):
        i1 = A_S * i1 + (1 - A_S) * drive
        v = A_M * v + (1 - A_M) * i1
        s = Spike.apply(v - 1.0, shape, beta)
        v = v - s.detach()
        nspk = nspk + s.detach().mean()
        i2 = A_S * i2 + (1 - A_S) * torch.bmm(s, p[1])
        u = A_M * u + (1 - A_M) * i2
        umax = torch.maximum(umax, u)
    return umax, nspk / T

def init(seed):
    g = torch.Generator().manual_seed(seed)
    w1 = torch.randn(5, NH, generator=g) * 1.5
    w2 = torch.randn(NH, 3, generator=g) * (10.0 / math.sqrt(NH))
    return [w1, w2]

def acc(p, x, y, shape, beta):
    with torch.no_grad():
        S = p[0].shape[0]; out, r = forward(p, x[None].expand(S, -1, -1), shape, beta)
        return (out.argmax(-1) == y[None]).float().mean(1).numpy(), float(r)

def run(shape, beta, d):
    xtr, ytr = map(torch.tensor, d["train"]); xte, yte = map(torch.tensor, d["test"])
    S = len(SEEDS); N = len(ytr)
    parts = [init(s) for s in SEEDS]
    p = [torch.stack([q[i] for q in parts]).requires_grad_(True) for i in range(2)]
    opt = torch.optim.Adam(p, lr=LR)
    gens = [np.random.RandomState(2000 + s) for s in SEEDS]
    for ep in range(EPOCHS):
        perms = torch.tensor(np.stack([g.permutation(N) for g in gens]))
        for b in range(0, N, BS):
            idx = perms[:, b:b + BS]
            out, _ = forward(p, xtr[idx], shape, beta)
            loss = torch.nn.functional.cross_entropy(out.reshape(-1, 3), ytr[idx].reshape(-1), reduction="none").view(S, -1).mean(1).sum()
            opt.zero_grad(); loss.backward(); opt.step()
    return acc(p, xte, yte, shape, beta)

if __name__ == "__main__":
    d = load(); os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    shapes = sys.argv[1].split(",") if len(sys.argv) > 1 else SHAPES
    out = os.path.join(HERE, "results", "arm_b.csv")
    new = not os.path.exists(out)
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["shape", "beta", "seed", "test_final", "hidden_rate"])
        if new: w.writeheader()
        for shape in shapes:
            for beta in BETAS:
                t = time.time(); a, r = run(shape, beta, d)
                for s, x in zip(SEEDS, a): w.writerow(dict(shape=shape, beta=beta, seed=s, test_final=round(float(x), 4), hidden_rate=round(r, 4)))
                f.flush()
                print(f"{shape} beta={beta}: {a.mean()*100:.2f} +- {a.std(ddof=1)*100:.2f} rate {r:.3f} ({time.time()-t:.0f}s)", flush=True)
