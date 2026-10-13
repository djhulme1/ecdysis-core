"""Nanda et al.'s grokking check (grok/nanda.py): the task's split; the model restricted to "=" against a plain
three-position transformer; the Fourier basis, key frequencies, the residual, the variance explained and the two logit
ablations on synthetic objects whose answers are known; the initial weights failing the sparsity checks; and a short,
repeatable training run.

Needs torch (the pinned PyTorch image). Run with: python3 -m unittest tests.test_nanda
"""

import importlib.util
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("grok_nanda", os.path.join(HERE, "..", "grok", "nanda.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)

import torch  # noqa: E402

SEED = "0" * 63 + "1"


def reference_forward(params, a, b):
    """A plain one-layer transformer over all three positions, causal, read at "="."""
    P, H, dh = M.P, M.N_HEADS, M.D_HEAD
    tok = torch.stack([a, b, torch.full_like(a, P)], 1)                         # N x 3
    x = params["W_E"][tok] + params["W_pos"][None]                               # N x 3 x d
    q = (x @ params["W_Q"]).view(-1, 3, H, dh)
    k = (x @ params["W_K"]).view(-1, 3, H, dh)
    v = (x @ params["W_V"]).view(-1, 3, H, dh)
    scores = torch.einsum("nqhe,nkhe->nhqk", q, k) / math.sqrt(dh)
    mask = torch.triu(torch.ones(3, 3, dtype=torch.bool), 1)
    scores = scores.masked_fill(mask, float("-inf"))
    att = torch.softmax(scores, -1)
    z = torch.einsum("nhqk,nkhe->nqhe", att, v).reshape(-1, 3, H * dh)
    x = x + z @ params["W_O"]
    x = x + torch.relu(x @ params["W_in"] + params["b_in"]) @ params["W_out"] + params["b_out"]
    return (x @ params["W_U"])[:, -1]


class Task(unittest.TestCase):
    def test_split(self):
        tr, te = M.split(SEED, 1)
        self.assertEqual((len(tr), len(te)), (3830, 12769 - 3830))
        self.assertEqual(len(set(tr.tolist()) | set(te.tolist())), 12769)
        tr2, _ = M.split(SEED, 1)
        self.assertTrue(torch.equal(tr, tr2))
        tr3, _ = M.split(SEED, 2)
        self.assertFalse(torch.equal(tr, tr3))


class Model(unittest.TestCase):
    def test_restricted_forward_equals_the_full_transformer(self):
        params = M.init_params(SEED, 1)
        a = torch.randint(0, M.P, (200,), generator=torch.Generator().manual_seed(3))
        b = torch.randint(0, M.P, (200,), generator=torch.Generator().manual_seed(4))
        with torch.no_grad():
            mine = M.forward(params, a, b)
            ref = reference_forward(params, a, b)
        self.assertEqual(mine.shape, (200, M.P))
        self.assertLess(float((mine - ref).abs().max()), 1e-4)

    def test_parameter_shapes(self):
        params = M.init_params(SEED, 1)
        self.assertEqual(tuple(params["W_E"].shape), (114, 128))
        self.assertEqual(tuple(params["W_U"].shape), (128, 113))
        self.assertEqual(sum(p.numel() for p in params.values()),
                         114 * 128 + 3 * 128 + 3 * 128 * 128 + 128 * 128 + 128 * 512 + 512 + 512 * 128 + 128
                         + 128 * 113)


class Analysis(unittest.TestCase):
    F = M.fourier_basis()

    def test_basis_and_round_trip(self):
        self.assertTrue(M.control_basis(self.F))
        self.assertEqual(tuple(self.F.shape), (113, 113))

    def test_synthetic_logits_and_neuron_logit_map(self):
        ok, det = M.control_synthetic_logits(self.F)
        self.assertTrue(ok, det)
        ok, det = M.control_synthetic_wl(self.F)
        self.assertTrue(ok, det)

    def test_owned_components(self):
        self.assertEqual(len(M.owned([5])), 8)
        self.assertEqual(len(M.owned([5, 9])), 16)
        self.assertNotIn((0, 0), M.owned([5]))

    def test_fve(self):
        x = torch.linspace(0, 20, 500, dtype=torch.float64)
        self.assertAlmostEqual(M.fve(3 * torch.cos(x) + 1, torch.cos(x)), 1.0, places=9)
        noise = torch.randn(500, generator=torch.Generator().manual_seed(5), dtype=torch.float64)
        self.assertLess(M.fve(noise, torch.cos(x)), 0.05)

    def test_initial_weights_fail_the_sparsity_checks(self):
        fails, n = M.sparsity_fails(M.init_params(SEED, 1), self.F)
        self.assertTrue(fails)
        self.assertGreater(n, M.KEYS_MAX)


class Training(unittest.TestCase):
    def test_short_run_learns_and_repeats(self):
        r1 = M.train(SEED, 1, epochs=200)
        r2 = M.train(SEED, 1, epochs=200)
        self.assertTrue(all(torch.equal(r1["final"][k], r2["final"][k]) for k in M.PARAM_ORDER))
        self.assertFalse(torch.equal(r1["final"]["W_E"], r1["initial"]["W_E"]))
        self.assertEqual([h["epoch"] for h in r1["history"]], [200])    # kept every 1,000 epochs and at the end
        a_te, b_te, y_te = r1["test"]
        self.assertEqual(len(a_te), 12769 - 3830)

    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", results=os.path.join(HERE, "_never"), epochs=1, runs=1)


if __name__ == "__main__":
    unittest.main()
