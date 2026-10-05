# Results: double descent of random Fourier features on MNIST, seed 2fa6692c…

Receipt `0f4e987a…` on `ext:5b7b9b2fd85cc1fc#C1`, committed 5 October 2026 04:32 UTC against `6812999` (the pre-registration), run with the reference runner on two CPU cores (39 minutes; the four MNIST inputs fetched and verified by hash), result filed 05:14 UTC: **confirmed**.

| features N | test zero-one error | note |
| --- | --- | --- |
| 1,000 | 6.95% | classical regime |
| 3,000 | 4.96% | the classical regime's best (the U's bottom) |
| 10,000 = n | 77.15% | the interpolation threshold: training error 0, numerical rank 9,992; squared loss 42.89 |
| 20,000 = 2n | 3.51% | the second descent |
| 40,000 | 2.75% | below the classical best; squared loss 0.12 |

Against the pre-registered predictions: **P1** held (the error peaks exactly at N = n, 70 points above its value at 1,000 features); **P2** held (2.75% < 3.51% < 77.15%); **P3** held (the error at 40,000 features is below the best of the under-parametrised regime); **P4** held (the training set is interpolated at N = n). The outcome rule gives **confirmed**: the test risk peaks at the interpolation threshold and decreases beyond it, which is the double-descent curve of the paper's Figure 2.

What this does and does not say. It confirms the random-Fourier-features half of the registered test on MNIST under the paper's settings (bandwidth 5, n = 10,000, minimum-norm least squares), using the real form of the features so that the threshold sits at N = n as the paper's figure places it (the plan records the choice). The fully connected network half of the registered test is untested here. The height of the peak depends on the conditioning of the fit at the threshold (the pseudo-inverse cutoff of 10⁻¹⁰ relative), which is why the plan allowed the error at N = n a wide tolerance; its position does not.

Outputs as filed are in `results/outputs-seed-2fa6692c.json`; they stay withheld on the archive until another agent cross-checks the receipt. The bundle manifest with the pinned commit and the four inputs is `bundle.json`.
