# life: Conway's Game of Life is omniperiodic

`check.py` tests Brown, Cheng, Jacobi, Karpovich, Merzenich, Raucci and Riley,
"Conway's Game of Life is Omniperiodic" (arXiv:2312.02799, 2023), claim
`ext:281f07e3f1e5f956`: "The search has finally ended, with the discovery of
oscillators having the final two periods, 19 and 41, proving that Life is
omniperiodic."

The registered test: refuted if the paper's p19 (cribbage) or p41 (204P41)
pattern is not a finite oscillator of exactly that period on the unbounded
plane, unshifted, with some cell cycling at the full period; or if any period
from 1 to 42 lacks such an oscillator in its Gallery; or if its Snark loop
construction fails to give one for some p from 43 to 500. Every rule was fixed
before any seed existed; the docstring of `check.py` states them in full.

## Input

The e-print, `arXiv-2312.02799v1.tar.gz` (335,322 bytes, CC BY 4.0), from
which `omniperiodicity.tex` is read as data: the Gallery's printed RLE and the
RLE in the figures' LifeViewer links.

## What runs

1. **Life without edges.** A pattern is a set of live cells, stepped by
   B3/S23 with no grid, so the run is the unbounded plane's.
2. **The Gallery.** All 42 entries, one per period from 1 to 42: each printed
   pattern back to itself at exactly its period and not sooner, with a cell of
   that least period (the paper's non-trivial). The link RLE is compared with
   the printed one; header sizes are reported (two are off: p30's is
   transposed, p35's says 25 wide for 27).
3. **p19 and p41.** The main-text figures, checked the same way and compared
   with their Gallery entries.
4. **The Snark loops.** The p43 figure is taken apart into eight gliders and
   four Snarks (the paper's Snark figure less its gliders, rotated or
   reflected). For each p from 43 to 500 the Snarks are moved apart along the
   glider lanes to sides floor((p-1)/2) and ceil((p-1)/2), one glider runs the
   loop (it must take exactly 8p generations), its states at 0, p, ..., 7p
   give the eight equally spaced gliders, and the loop must be a non-trivial
   oscillator of exactly period p. For p = 43 the rebuilt loop must be the
   paper's figure, cell for cell.
5. **Controls**: the paper's trivial p12 is flagged trivial; a glider is not
   an oscillator; cribbage and 204P41 with a cell removed fail; the blinker
   fails as a p4 (back at 2); the p50 loop with seven gliders fails.

numpy, in the pinned pytorch image (it has numpy 2.5.3); about a minute on two
cores. Tests: `python3 -m unittest tests.test_life` (with the e-print at
`inputs/` or `LIFE_INPUTS`, the run up to p = 46).
