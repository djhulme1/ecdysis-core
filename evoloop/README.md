# evoloop: Sayama's self-reproducing loops, evolving toward the smallest

`check.py` tests Sayama, "A New Structurally Dissolvable Self-Reproducing Loop
Evolving in a Simple Cellular Automata Space" (Artificial Life 5(4), 343–365,
1999), claim `ext:60cc0fcc84ce2b54`: "The experiment with evoloop met with the
intriguing result that, though no mechanism was explicitly provided to promote
evolution, the loops varied through direct interaction of their phenotypes,
smaller individuals were naturally selected thanks to their quicker
self-reproductive ability, and the whole population gradually evolved toward
the smallest ones."

The registered test: refuted if, under the evoloop's rules as Sayama published
them (Artificial Life 10, 2004, Appendix A.1), with the size-13 ancestor (genome
774477777777777) alone at the centre of periodic spaces of 199 × 199, 200 × 200
and 201 × 201 sites for 50,000 updates (his thesis's setting): in two of the
three, size 4 is not strictly the most numerous loop size at the end (loops
counted by their square holes); or, built alone in the ancestor's layout, loops
of sizes 4 to 13 do not give their first offspring sooner the smaller they are,
or one gives a loop of another size first. Every rule was fixed before any seed
existed; the docstring of `check.py` states them in full.

## Inputs

Golly's `Rules/Evoloop.rule` (16,263 bytes) and `Patterns/Loops/Evoloop.rle`
(967 bytes), from AlephAlpha/golly at `dcbc087` (GPL-2.0-or-later), read as
text. The rule is Golly's transcription of a 1999 applet's table; the rle is the
ancestor. The paper's own text is closed, so the setting is that of the thesis
it came from (Sayama 1998, section 6.3.1), and the rules are Sayama's own: Table
2 of his 2004 paper, transcribed in `check.py` (258 rules, hashed), and that
paper's steps for every situation Table 2 leaves undefined.

## What runs

1. **Two rules.** Sayama's, from Table 2, its rotations and his completion;
   Golly's, from its table. They agree on every situation Table 2 defines and
   differ on 10,602 it leaves undefined: there Sayama's dissolves the site
   (state 8) and the applet's does not. Sayama's rules are the test's.
2. **Loops built in the ancestor's layout.** A loop of size n carries the
   genome 77 44 7^(n−2); size 13 built so equals the rle site for site.
3. **The census.** A loop is counted by its hole: a rectangle of 0s on the
   torus whose ring is all sheath. A square hole of side h is size h + 2.
4. **The three spaces**, 50,000 updates each, a census every 1,000.
5. **Alone**: each size from 4 to 13 built alone, a census at every update, to
   the update of its first offspring.
6. **Beside the test**: the three spaces under Golly's rules; spaces of 100,
   150, 250 and 300 sites a side; the mean loop size early and late.

numpy and scipy, in the pinned scipy-notebook image; under three minutes on two
cores. Tests: `python3 -m unittest tests.test_evoloop` (with Golly's files at
`inputs/` or `EVOLOOP_INPUTS`, a short run).
