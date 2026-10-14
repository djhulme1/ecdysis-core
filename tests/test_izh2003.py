"""Izhikevich's simple model (snn/izh2003.py): the rest state; one Euler step and one step of net.m's scheme worked
by hand; the reset rule; the train analysis on trains built here; the threshold bisection on a stand-in; net.m's
reader on texts written here; the spectrum on a built rhythm; the verdict at and beside each condition; the seed
refused. The paper's files are not read here, and none of the five types is run under the test's protocol.

Run with: python3 -m unittest discover -s tests -p test_izh2003.py
"""

import importlib.util
import math
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_izh2003", os.path.join(HERE, "..", "snn", "izh2003.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

NET = ("% a comment\r\nNe=800;                 Ni=200;\r\nre=rand(Ne,1);          ri=rand(Ni,1);\r\n"
       "a=[0.02*ones(Ne,1);     0.02+0.08*ri];\r\nb=[0.2*ones(Ne,1);      0.25-0.05*ri];\r\n"
       "c=[-65+15*re.^2;        -65*ones(Ni,1)];\r\nd=[8-6*re.^2;           2*ones(Ni,1)];\r\n"
       "S=[0.5*rand(Ne+Ni,Ne),  -rand(Ne+Ni,Ni)];\r\nv=-65*ones(Ne+Ni,1);    % Initial values of v\r\n"
       "u=b.*v;                 % Initial values of u\r\nfor t=1:1000            % simulation of 1000 ms\r\n"
       "  I=[5*randn(Ne,1);2*randn(Ni,1)]; % thalamic input\r\n  fired=find(v>=30);    % indices of spikes\r\n"
       "  v(fired)=c(fired);\r\n  u(fired)=u(fired)+d(fired);\r\n  I=I+sum(S(:,fired),2);\r\n"
       "  v=v+0.5*(0.04*v.^2+5*v+140-u+I); % step 0.5 ms\r\n  u=u+a.*(b.*v-u);                 % stability\r\n"
       "end;\r\n")
TOY = (0.03, 0.15, -60.0, 5.0)      # not one of the paper's types


class Model(unittest.TestCase):
    def test_rest(self):
        for b in (0.15, 0.2, 0.25, 0.26):
            v, u = M.rest(b)
            self.assertAlmostEqual(0.04 * v * v + 5 * v + 140 - u, 0.0, places=9)
            self.assertAlmostEqual(u, b * v)
        self.assertAlmostEqual(M.rest(0.2)[0], -70.0)
        with self.assertRaises(ValueError):
            M.rest(0.5)

    def test_one_euler_step_by_hand(self):
        v0, u0, i = -60.0, -10.0, 4.0
        dv = 0.04 * 3600 - 300 + 140 + 10 + 4
        v1 = v0 + 0.1 * dv
        u1 = u0 + 0.1 * 0.03 * (0.15 * v1 - u0)
        _, vs, (v, u) = M.simulate(TOY, lambda t: i, 0.1, state=(v0, u0), trace=True)
        self.assertAlmostEqual(v, v1)
        self.assertAlmostEqual(u, u1)
        self.assertEqual(len(vs), 1)

    def test_netm_step_by_hand(self):
        v0, u0, i = -60.0, -10.0, 4.0
        f = lambda v: 0.04 * v * v + 5 * v + 140 - u0 + i
        v1 = v0 + 0.5 * f(v0)
        v1 = v1 + 0.5 * f(v1)
        u1 = u0 + 0.03 * (0.15 * v1 - u0)
        _, _, (v, u) = M.simulate(TOY, lambda t: i, 1.0, scheme="netm", state=(v0, u0), trace=True)
        self.assertAlmostEqual(v, v1)
        self.assertAlmostEqual(u, u1)

    def test_reset(self):
        spikes, _, (v, u) = M.simulate(TOY, lambda t: 0.0, 0.1, state=(31.0, 1.0), trace=True)
        self.assertEqual(spikes, [0.0])
        self.assertLess(v, 30)
        self.assertAlmostEqual(u, 6.0 + 0.1 * 0.03 * (0.15 * v - 6.0))

    def test_current_and_window(self):
        cur = M.step_current(7.0)
        self.assertEqual([cur(49.9), cur(50.0), cur(349.9), cur(350.0)], [0.0, 7.0, 7.0, 0.0])
        self.assertEqual(M.in_step([10, 50, 200, 349.9, 350]), [50, 200, 349.9])


class Trains(unittest.TestCase):
    def test_structure(self):
        reg = M.structure([20.0 * k for k in range(8)])
        self.assertFalse(reg["bursting"])
        self.assertAlmostEqual(reg["gap"], 1.0)
        ib = M.structure([0, 4, 8, 40, 72, 104])
        self.assertTrue(ib["bursting"])
        self.assertEqual(ib["bursts"], [(0, 3)])
        ch = M.structure([0, 3, 30, 33, 60, 63, 66, 95])
        self.assertEqual(ch["bursts"], [(0, 2), (2, 2), (4, 3)])
        self.assertFalse(M.structure([0, 5])["bursting"])                 # one interval: no gap to see
        self.assertFalse(M.structure([0, 10, 25, 44])["bursting"])        # ratios 1.5 and 1.27

    def test_adaptation_and_rate(self):
        self.assertAlmostEqual(M.adaptation([0, 10, 22, 37, 56]), 1.9)
        self.assertIsNone(M.adaptation([5]))
        self.assertAlmostEqual(M.rate([1] * 30), 100.0)

    def test_threshold_bisection(self):
        saved = M.fires
        try:
            M.fires = lambda p, amp, dt=0.1, scheme="euler": amp >= 3.217
            th = M.threshold(TOY)
            self.assertLessEqual(abs(th - 3.217), 0.005)
            self.assertGreaterEqual(th, 3.217)
            M.fires = lambda p, amp, dt=0.1, scheme="euler": True
            self.assertIsNone(M.threshold(TOY))
        finally:
            M.fires = saved


class Verdict(unittest.TestCase):
    def found(self, **kw):
        def train(spikes, bursting=False, bursts=(), ad=1.0, rate=10.0):
            return {"structure": {"spikes": spikes, "bursting": bursting, "bursts": list(bursts), "intervals": [],
                                  "gap": 1.0}, "adaptation": ad, "rate": rate}
        f = {"RS": train(8, ad=2.0, rate=20.0), "IB": train(9, True, [(0, 3)]), "CH": train(12, True, [(0, 3)] * 4),
             "FS": train(30, ad=1.05, rate=100.0), "LTS": train(20, ad=1.6, rate=60.0)}
        for key, v in kw.items():
            name, field = key.split("_", 1)
            if field in ("adaptation", "rate"):
                f[name][field] = v
            else:
                f[name]["structure"][field] = v
        return f

    def test_conditions(self):
        th = {"RS": 4.0, "LTS": 1.0}
        c = M.conditions(self.found(), th)
        self.assertEqual(len(c), 5)
        self.assertTrue(all(c.values()))
        for kw in ({"RS_adaptation": 1.2}, {"RS_bursting": True}, {"IB_bursts": [(1, 3)]},
                   {"IB_spikes": 5}, {"CH_bursts": [(0, 2)] * 2}, {"FS_rate": 39.0},
                   {"FS_adaptation": 1.7}, {"LTS_rate": 15.0}, {"LTS_adaptation": 1.25}):
            self.assertEqual(sum(M.conditions(self.found(**kw), th).values()), 4, kw)
        self.assertEqual(sum(M.conditions(self.found(), {"RS": 1.0, "LTS": 1.0}).values()), 4)
        self.assertEqual(sum(M.conditions(self.found(), {"RS": None, "LTS": 1.0}).values()), 4)

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


class Inputs(unittest.TestCase):
    def test_net_reader(self):
        self.assertEqual(M.check_net(NET.encode("ascii")), 18)
        with self.assertRaises(M.Refused):
            M.check_net(NET.replace("0.25-0.05*ri", "0.25-0.04*ri").encode("ascii"))
        with self.assertRaises(M.Refused):
            M.check_net("Ne=800;\xe9".encode("latin-1"))

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for name, _, _ in M.INPUTS:
                with open(os.path.join(d, name), "wb") as fh:
                    fh.write(b"x")
            with self.assertRaises(M.Refused):
                M.read_inputs(d)

    def test_spectrum(self):
        counts = [5 + 3 * math.sin(2 * math.pi * 10 * k / 1000) + 2 * math.sin(2 * math.pi * 40 * k / 1000)
                  for k in range(1000)]
        peaks, power = M.spectrum_peaks(counts)
        self.assertEqual(peaks, [10, 40])
        self.assertGreater(power[10], power[40])


if __name__ == "__main__":
    unittest.main()
