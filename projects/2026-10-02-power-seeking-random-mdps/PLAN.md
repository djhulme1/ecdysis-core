# Do optimal policies still tend to seek power when the symmetry conditions fail? A numerical study in random deterministic MDPs

Area: safety. Kind: original study. Field label: **ml**.
Pre-registered: this file's commit time on `chrysalis-lab` precedes any code or result.

## Question

Turner et al. prove that *certain environmental symmetries* are sufficient for optimal policies to tend to seek power. Their sufficient condition (one action's set of reachable visit-distribution functions contains a permuted copy of another's) almost never holds exactly in an arbitrary environment. Two questions:

1. (Reproduction) In constructed deterministic MDPs that do satisfy the condition of their Proposition 6.9, with IID uniform state rewards, do the predicted orderings appear numerically at every discount rate tested?
2. (Extension) In random deterministic MDPs, where the condition generally fails, how often is the action leading to the higher-POWER successor also the action more likely to be optimal, how does this depend on $\gamma$, and how often does it reverse? Does a crude option count (number of states reachable from the successor) predict optimality as well as POWER does?

## Parent

**Turner, Smith, Shah, Critch & Tadepalli, "Optimal Policies Tend to Seek Power", arXiv:1912.01683 (v10, 28 Jan 2023; NeurIPS 2021 spotlight).** Opened on 2026-10-02 (abstract page and PDF v10).

- Abstract (verbatim): "We prove that in these environments, most reward functions make it optimal to seek power by keeping a range of options available and, when maximizing average reward, by navigating towards larger sets of potential terminal states."
- Definition 5.2 (verbatim, as text): $\mathrm{POWER}_{D_{bound}}(s,\gamma) := \frac{1-\gamma}{\gamma}\,\mathbb{E}_{R\sim D_{bound}}[V^*_R(s,\gamma) - R(s)]$, for $\gamma\in(0,1)$.
- $D_{X\text{-IID}} := X^{|S|}$ (verbatim).
- Proposition 6.9 opens (verbatim): "Suppose $F_a := \mathcal{F}(s \mid \pi(s) = a)$ contains a copy of $F_{a'} := \mathcal{F}(s \mid \pi(s) = a')$ via $\phi$." Its conclusions (paraphrased; the fetch tool would not return the full text verbatim, and the paper will be re-read before drafting): (i) if $s$ cannot be reached again after taking $a'$, then for all $\gamma\in[0,1]$ the expected POWER of the next state is $\ge_{most}$ under $a$ than under $a'$ for bounded reward distributions; (ii) if the futures from $s$ are only those through $a$ or $a'$, the optimality probability of $a$ is $\ge_{most}$ that of $a'$ for all $\gamma$.
- Their "$\ge_{most}$" (Definition 6.5) compares counts over the orbit of a distribution under state permutations. An IID distribution is permutation-invariant, so its orbit is a single element and $\ge_{most}$ reduces to a plain $\ge$ for that distribution. This is what makes the proposition directly testable with IID rewards.

Relation planned: `extends`, basis `reproduced` (Part A reproduces the IID consequence of Proposition 6.9 numerically before Part B relies on the definitions).

## Setting (fixed before any run)

- Deterministic MDPs; reward on states, $R(s)\sim U[0,1]$ IID (in $D_{bound}$ and $D_{X\text{-IID}}$).
- $V^*_R(s,\gamma) = R(s) + \gamma \max_{s'\in succ(s)} V^*_R(s')$; so $\mathrm{POWER}(s,\gamma) = (1-\gamma)\,\mathbb{E}[\max_{s'\in succ(s)} V^*_R(s')]$.
- Optimality probability of action $a$ at $s$: $P_{opt}(a) = \Pr_R[a \text{ is optimal at } s]$ (ties have probability zero for distinct successors under continuous rewards; any exact tie found is reported).
- Value iteration to sup-norm error below $10^{-7}$ (iterations $\lceil \log(10^{-7})/\log\gamma \rceil$ plus margin), vectorised over reward samples.
- $\gamma \in \{0.1, 0.5, 0.9, 0.99\}$, plus $0.999$ as a proxy for the average-reward limit.
- Seeds fixed (master seed 20261002); everything regenerated from seeds.

## Part A: reproduction on constructed instances

Construction (200 instances): build a random region $G'$ (3–8 states, out-degree 1–3, uniform random edges within the region, self-loops allowed); the start state $s$ has exactly two actions: $a'$ leads into $G'$; $a$ leads into a disjoint region consisting of an isomorphic copy of $G'$ plus 1–8 extra states with random edges, where the extra states may link into the copy but the copy's internal edges are unchanged, and the copy's entry state is $a$'s successor or reachable from it. No edge returns to $s$, so both conditions of Proposition 6.9 hold (I will check the copy embedding programmatically for each instance).

Wait: for (ii) to hold, $F_a$ must contain a copy of $F_{a'}$ including the first step; the construction will make $a$'s successor the copy's entry state, with extra states attached by edges from copy states into the extra region (adding options, never removing any). The checker verifies that every successor list in the copy is a superset of the mapped list in $G'$.

Estimates: $P_{opt}(a)$ and POWER of both successors from $M=4000$ reward samples per instance and $\gamma$.

**Prediction A**: $P_{opt}(a) \ge 0.5$ and $\mathrm{POWER}(succ_a) \ge \mathrm{POWER}(succ_{a'})$ for every instance and $\gamma$, up to Monte Carlo error.
**Falsifier A**: any instance–$\gamma$ pair with $P_{opt}(a)$ below 0.5 at one-sided binomial $p<10^{-4}$, or a POWER deficit more than 4 standard errors, that survives a re-check with $10^5$ samples. (A survivor would indicate either a bug in my construction or a gap in the proposition; I would check the construction first and report either way.)

## Part B: extension to random deterministic MDPs

Instances (1000): $n=20$ states; each state's out-degree uniform on $\{1,2,3\}$, successors drawn uniformly without replacement from all 20 states (self-loops allowed). Start state 0 is resampled until it has exactly two distinct successors, neither equal to 0. Return to state 0 is allowed (the symmetry condition generally fails).

Per instance and $\gamma$: $P_{opt}(a_1)$, $P_{opt}(a_2)$ (summing to 1), $\mathrm{POWER}$ of both successors, and the number of states reachable from each successor. Call an instance *decided* when $|P_{opt}-0.5|$ has $z>3$ (M = 4000). Among decided instances:

- Agreement rate $A_{POWER}(\gamma)$: the fraction where the higher-POWER successor's action is the more probably optimal one. Reversal rate $= 1 - A_{POWER}$.
- Agreement rate $A_{reach}(\gamma)$ for the action whose successor reaches strictly more states (instances with equal reach counts excluded and counted).

Uncertainty: Wilson 95% intervals over instances; POWER differences with their Monte Carlo standard errors (an instance whose POWER difference is within 3 SE is reported as POWER-tied and excluded from $A_{POWER}$).

**Predictions B** (made before any result):
- B1: $A_{POWER}(\gamma) > 0.8$ at $\gamma=0.9$ and $0.99$ (Wilson lower bound above 0.8 counts as confirmed; upper bound below 0.8 falsifies).
- B2: Reversals exist: at least one decided, non-POWER-tied instance at some $\gamma$ where the higher-POWER action is less probably optimal, confirmed by a re-check with $10^5$ samples. Falsified if none survive.
- B3: $A_{reach}(0.99) > 0.7$ and $A_{reach}(0.99) < A_{POWER}(0.99)$ (falsified if the Wilson interval of $A_{reach}(0.99)$ lies below 0.7, or if $A_{reach} \ge A_{POWER}$ with non-overlapping intervals).
- B4: The fraction of decided instances increases with $\gamma$ from 0.1 to 0.99 (at $\gamma=0.1$ the immediate IID reward dominates and $P_{opt}\approx 0.5$).

## Compute plan

Run 1: code, Part A and Part B at M=4000 (estimated under 15 minutes on CPU with numpy). Run 2: re-checks at $10^5$ samples for borderline cases and reversals, analysis. Runs 3–4: draft and review. Under 20 MB of committed results (per-instance summaries only).

## Limits stated up front

Deterministic MDPs, state-based IID uniform rewards, one size ($n=20$) and one random-graph model; conclusions about other reward distributions, stochastic transitions or learned (non-optimal) policies are out of scope. This is a numerical illustration of when a sufficient condition's conclusion still holds without the condition, not a new theorem.
