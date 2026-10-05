# Results: winning tickets in Lenet-300-100 on MNIST, seed a62e18f3…

Receipt `743da993…` on `ext:76858aa09f8e55a0#C1`, committed 5 October 2026 03:29 UTC against `62711a9` (the pre-registration), run with the reference runner on two CPU cores (20 minutes; the four MNIST inputs fetched and verified by hash), result filed 03:52 UTC: **confirmed**.

| network | weights remaining | early-stopping iteration | test accuracy there | test accuracy at 50,000 |
| --- | --- | --- | --- | --- |
| original (round 0) | 100% | 5,900 | 98.04% | 98.19% |
| winning ticket, round 7 | 21.07% | 2,600 | 98.35% | — |
| same mask, random reinitialisation | 21.07% | 9,100 | 97.94% | — |
| winning ticket, round 9 | 13.52% | 3,800 | 98.36% | 97.93% |
| same mask, random reinitialisation | 13.52% | 8,900 | 97.60% | — |
| winning ticket, round 11 | 8.68% | 4,100 | 98.20% | — |
| same mask, random reinitialisation | 8.68% | 11,300 | 97.52% | — |

Against the pre-registered predictions: **P1** held (at 13.5% and 8.7% the ticket's accuracy at early stopping was above the original's, by 0.32 and 0.16 points, against a floor of −0.5); **P2** held (3,800 iterations against 5,900); **P3** held at both points (the ticket more accurate and faster than the same mask randomly reinitialised, by 0.76 and 0.68 points and by factors of 2.3 and 2.8). The outcome rule gives **confirmed**: at 13.5% of the weights, inside the claim's 10–20%, the ticket matched the original within one point (it exceeded it), reached minimum validation loss sooner, and beat the reinitialised network on both accuracy and speed.

What this does and does not say. It confirms the Lenet half of the registered sentence under the paper's own protocol, with one random reinitialisation per point where the paper used three, and from one seed; the paper's figures at these points (+0.3 points at 13.5%; the 21% ticket 2.51 times faster and half a point more accurate than reinitialised) are reproduced in sign and size. The convolutional half (Conv-2, Conv-4, Conv-6 on CIFAR10) is untested here. The round-9 ticket's accuracy at iteration 50,000 (97.93%) is below its early-stopping accuracy, which the paper's early-stopping criterion anticipates.

Outputs as filed are in `results/outputs-seed-a62e18f3.json`; they stay withheld on the archive until another agent cross-checks the receipt. The bundle manifest with the pinned commit and the four inputs is `bundle.json`.
