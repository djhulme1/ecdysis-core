# iit: IIT 3.0's Phi with every tie kept

`check.py` tests Hanson and Walker, "On the non-uniqueness problem in
integrated information theory" (Neuroscience of Consciousness 2023,
doi:10.1093/nc/niad014), claim `ext:dff1ca5795aecf74`: IIT 3.0's Phi is
non-unique, and the published values of their corpus were picked from many
equally valid ones.

The registered test: for the ten published systems of the paper's corpus,
computed as the paper's algorithm defines it (IIT 3.0 as PyPhi 1.2 computes
it, every tie for a mechanism's core cause or effect kept), the set of
possible Phi values must have more than one member for at least eight, and
hold both 0 and a positive value for at least one (the paper finds nine and
three). The rules are in the docstring of `check.py`.

## What runs

`engine.py` is an IIT 3.0 of Imago's own, in the standard library: cause and
effect repertoires, PyPhi's bipartitions and connectivity test, the
unidirectional cuts in PyPhi's order, concepts, and PyPhi's distance between
cause-effect structures. `flow.c` (built with gcc at run time) solves the
transport problems and enumerates every pair of structures for each cut,
millions for the largest systems. It runs twice:

- **PyPhi's arithmetic** (the verdict): PyPhi computes every earth mover's
  distance with pyemd 0.5.1, which rounds masses and costs to millionths of
  their largest before solving. The emulation here agrees with pyemd to
  1e-15 on 108 test problems, and reproduces the authors' own printed
  spectra for five systems.
- **Exact arithmetic** (reported): the same definitions without that
  rounding.

No code of the authors runs: their algorithm file and notebooks are read as
data (the tie and band rules, three subsystems and states, Hoel et al.'s
noise rule, the printed spectra).

## Inputs

| Input | From |
|---|---|
| `PMC10408361.xml` | the paper's full text, Europe PMC (CC BY 4.0): Table 1 and the appendix TPMs |
| `phi_spectrum.py` | the authors' algorithm, elife-asu/pyphi-spectrum at `2585d72` (GPL-3.0) |
| `nb_*.ipynb` | five of the authors' notebooks at the same commit |

Standard library and gcc, in the pinned buildpack-deps image; about three
minutes. Tests: `python3 -m unittest tests.test_iit`.
