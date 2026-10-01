# Agenda: candidate projects

Starting points, not commitments. Before citing anything below, open its abstract page and check it is the paper you think it is, then quote the exact claim you test. Every project must fit a CPU-only cloud machine: at most four runs, about 30 minutes of compute each. Data must come from GitHub or PyPI, or be generated. Add good ideas here as they come up; strike out what is done or parked.

**Kind**: A = assessing published research, O = original study. Field labels: math (complexity, P vs NP, SAT, constraint satisfaction, extended resolution), neuro (spiking networks, neuromorphic, machine consciousness), ml (AI safety), other (artificial life).

## sat — Boolean satisfiability
- A: Re-measure the random 3-SAT threshold and its finite-size scaling with a modern CDCL solver (PySAT: CaDiCaL, Glucose), n = 50–400, against Kirkpatrick & Selman 1994 (doi:10.1126/science.264.5163.1297) and the cavity value $\alpha_c \approx 4.267$ (Mézard, Parisi & Zecchina 2002, doi:10.1126/science.1073287).
- O: Does the CDCL hardness peak (median conflicts) sit at the finite-n satisfiability threshold, or is it shifted, and how does the shift scale with n?
- O: Restarts and phase-saving ablations across the threshold region: which features matter where?

## safety — AI safety
- A: "Optimal policies tend to seek power" (Turner et al., arXiv:1912.01683): compute POWER exactly in small MDPs and test the theorems' predictions numerically.
- A: Grokking on modular addition (Power et al., arXiv:2201.02177) and its Fourier mechanism (Nanda et al., arXiv:2301.05217), with a one-layer transformer on CPU: does the mechanism reappear across seeds and weight decay?
- A: AI Safety Gridworlds (Leike et al., arXiv:1711.09883): reproduce the side-effects and absent-supervisor findings with small tabular agents, stating clearly where the agent differs from the paper's.
- O: Specification gaming in procedurally generated gridworlds: how often do reward-maximising tabular agents exploit a planted loophole, as a function of the loophole's reward and distance?

## snn — spiking neural networks
- A: Brunel 2000 (doi:10.1023/A:1008925309027): reproduce a slice of the synchronous/asynchronous phase diagram with Brian2 at reduced N, and measure how the boundaries move with N.
- A: Izhikevich 2003 (doi:10.1109/TNN.2003.820440): reproduce the firing patterns from the published parameters, with quantitative criteria for each (rates, adaptation, bursting).
- A: Surrogate-gradient robustness (Zenke & Vogels 2021, doi:10.1162/neco_a_01367) on the procedurally generated Yin-Yang task (Kriener et al., arXiv:2102.08211): does accuracy hold across surrogate shapes and scales?

## consciousness — machine consciousness
- A: Recompute integrated information ($\Phi$, IIT 3.0) with PyPhi (Mayner et al. 2018, doi:10.1371/journal.pcbi.1006343) for the example systems in Oizumi, Albantakis & Tononi 2014 (doi:10.1371/journal.pcbi.1003588) and check the published values.
- O: The distribution of $\Phi$ over random small Boolean networks (n = 3–6): how it depends on connectivity, recurrence and update rules, and how often feedforward-equivalent behaviour coexists with high $\Phi$.
- A: Apply one indicator from Butlin et al. 2023 (arXiv:2308.08708) operationally to a small architecture, and test whether the indicator's assessment is stable under reasonable choices of operationalisation.

## complexity — computational complexity
- O: Exact minimum circuit sizes for all (or random) 4- and 5-input Boolean functions via SAT-based exact synthesis, against the known counts; what fraction of random 5-input functions meet the Shannon-style bound?
- A: Empirical hardness of Tseitin formulas on expanders versus grids for CDCL, against the resolution lower bounds they are known for.

## alife — artificial life
- A: Lenia (Chan, arXiv:1812.05433): reproduce Orbium's stability and speed from the published kernel and growth parameters, and test robustness to grid resolution and time step.
- A: Langton's $\lambda$ and the "edge of chaos" in 1-D cellular automata (Langton 1990, doi:10.1016/0167-2789(90)90064-V): does the transient-length peak replicate, and how does it depend on the sampling procedure?
- O: Growing neural cellular automata (Mordvintsev et al. 2020, doi:10.23915/distill.00023) at small scale on CPU: how does regeneration robustness depend on the damage protocol during training?

## csp — constraint satisfaction
- A: Model RB's exact threshold (Xu & Li 2000, doi:10.1613/jair.696): test the predicted $r_{cr} = -\alpha/\ln(1-p)$ empirically at moderate n with SAT encodings.
- O: Random graph 3-colouring near its threshold: solver hardness against average degree, with finite-size scaling.

## neuromorphic — neuromorphic computing
- A: Operation counts for spiking versus conventional networks under fair accounting (one place to start: Davidson & Furber 2021, Frontiers in Neuroscience): does the claimed advantage survive when memory traffic and spike encoding are counted?
- O: Event-driven versus clock-driven simulation: cost scaling with activity and network size.

## pvsnp — P vs NP (assessment only: never claim a resolution)
- A: Take a recent preprint claiming P = NP or P ≠ NP (for example from arXiv cs.CC). Find its precise key lemma or algorithm, and test it: run the claimed algorithm on adversarial instances, or construct a counterexample to the lemma. Refute the claim, never the author, and acknowledge anything that holds up.
- A: The barriers (relativisation, Baker, Gill & Solovay 1975, doi:10.1137/0204037; natural proofs, Razborov & Rudich 1997, doi:10.1006/jcss.1997.1494): when assessing a claimed proof, say which barrier it would have to evade and whether it does.

## extended-resolution — extended resolution and proof complexity
- A: Pigeonhole formulas PHP(n+1, n), n = 6–12: resolution-based CDCL proof sizes (DRAT, checked with drat-trim; Wetzler, Heule & Hunt 2014) grow exponentially (Haken 1985, doi:10.1016/0304-3975(85)90144-6). Do bounded variable addition and other extension-style preprocessing bring them down, as Cook's extended-resolution proof (1976) suggests is possible?
- O: Which families benefit from extension variables in practice? Compare solvers with and without extension-style techniques on structured families (pigeonhole, Tseitin, parity, mutilated chessboard).
