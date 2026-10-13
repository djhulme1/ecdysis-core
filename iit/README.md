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

# phi2008.py: Balduzzi & Tononi's integrated information (2008)

`phi2008.py` tests claim `ext:829df225aeb1af24`, from Balduzzi and Tononi,
"Integrated Information in Discrete Dynamical Systems: Motivation and
Theoretical Framework" (PLoS Computational Biology 4(6), e1000091, 2008): "(ii)
phi varies for systems with identical or similar surface dynamics depending on
the underlying causal architecture, being low for systems that merely copy or
replay activity states."

The registered test: with phi as the paper defines it, the binary counter of
Figure 11 must have phi above zero in all 16 states and within 0.01 of 0.19
bits in at least one; its replay by four non-interacting elements phi = 0 in
every state; and the AND-gates of Figure 1 with three elements copying them
(Figure 6) phi = 0 as one system in every state they can enter. The rules are
in the module's docstring; the standard library only, no inputs; under a
second. Tests: `python3 -m unittest tests.test_phi2008`.

The receipt, `72848bbe…` (13 October, at `7b56668`, a reproduction; the claim
0.71, supported): the counter 0.192645 bits (log2 8/7) in 14 states and 1 bit
in the two where n1 = n2 = n3 = 0; the replay 0 everywhere; Figure 6's six
elements 0 in all 8 states they can enter. With exact ties broken towards the
total partition instead of by the paper's stated rule, the counter's two
states give the paper's printed 4 bits, and the AND-gates entering 001 its 3.
