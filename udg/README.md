# udg: a 553-vertex unit-distance graph with chromatic number 5

`check.py` tests Heule, "Computing Small Unit-Distance Graphs with Chromatic
Number 5" (Geombinatorics 28(1), 2018; arXiv:1805.12181), claim
`ext:33129411bee32407`: "Our method, which is based on clausal proof
minimization, allowed us to compute several 553-vertex unit-distance graphs
with chromatic number 5, while the smallest published unit-distance graph with
chromatic number 5 has 1581 vertices."

The registered test: refuted if the 553-vertex graph released with the paper
is not 553 distinct points in the plane, lists an edge whose endpoints are not
at distance exactly 1, has a proper colouring with 4 colours, or has none with
5. The paper computed several such graphs and released one; the test takes
that one. Every rule was fixed before any seed existed; the docstring of
`check.py` states them in full.

## Inputs

The claim's data of record, from marijnheule/CNP-SAT at `a238bb0` (30 May
2018, the day of the arXiv submission; the repository states no licence, and
the paper names it as the home of its graphs and proofs), and the tools of
`hexagon/check.py`:

| Input | From | Bytes |
|---|---|---|
| `heule553.vtx` | `vtx/553.vtx`: the points, `{x, y}` in Mathematica syntax | 28,611 |
| `heule553.edge` | `edge/553.edge`: DIMACS, 2,722 edges | 25,710 |
| `heule553-4.cnf` | `cnf/553-4.cnf`: the 4-colouring formula | 149,821 |
| `heule553-4-sbp.cnf` | `cnf/553-4-sbp.cnf`: the same with three symmetry-breaking units | 149,834 |
| `heule553-4-sbp.drat` | `proof/553-4-sbp.drat`: Glucose's DRAT proof | 4,143,373 |
| `cadical_2.1.3.orig.tar.gz` | Debian's archived source of CaDiCaL 2.1.3 | 731,545 |
| `cake_lpr.S`, `basis_ffi.c` | tanyongkiam/cake_lpr at `a36874a` | 2,473,208 and 12,736 |

## What runs

1. **The points, exactly.** Each coordinate is read as an element of
   Q(√3, √5, √11), a sum of rational multiples of √1, √3, √5, √11, √15, √33,
   √55 and √165, with quotients formed through conjugates; any other radical
   is refused. 553 distinct points.
2. **The edges, exactly.** Every edge's squared length must be exactly 1.
   Unit pairs the file does not list are counted beside it, found by screening
   every pair in floating point and testing the near ones exactly.
3. **No 4-colouring, verified.** The 4-colouring formula is written from the
   edges (it must equal the released one, clause for clause, and the
   symmetry-broken one must add three units colouring a triangle) and refuted
   by CaDiCaL with its LRAT proof streamed into the CakeML-verified checker
   cake_lpr.
4. **A 5-colouring.** CaDiCaL's model of the 5-colouring formula, checked edge
   by edge.
5. **The released proof** (reported only): every lemma of Heule's DRAT proof
   up to the refutation is RUP against the symmetry-broken formula, by a
   forward checker of Imago's own (not a verified one).
6. **Controls**: a vertex moved by 10⁻⁹ breaks an edge; a colouring with an
   edge's ends alike fails; the graph without the 5-colouring's smallest colour
   class is 4-colourable, the model checked; and the three pigeonhole proof
   controls of `hexagon/check.py`.

Standard library and gcc, in the pinned buildpack-deps image. Tests:
`python3 -m unittest tests.test_udg` (the Moser spindle, a 4-chromatic
unit-distance graph in the same field, among them).
