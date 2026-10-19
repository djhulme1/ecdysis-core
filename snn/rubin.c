/* Rubin, Lee & Sompolinsky (2001): 1000 excitatory synapses on independent Poisson inputs driving one
 * integrate-and-fire cell, under the additive or the multiplicative temporally asymmetric Hebb rule.
 * The rules are in snn/rubin.py; this is its simulator.
 *
 * Usage:
 *   rubin run   w0 w1 w2 w3 rule rate_hz gs warm_s meas_s start plastic snap_steps window_steps out_prefix
 *   rubin pair  rule dt_ms w          (one synapse at w; a pre spike at step 1000 and a post spike dt_ms later,
 *                                      post minus pre; prints the change of w)
 *   rubin const g                     (the cell under a constant conductance g from V = 0; prints the time of its
 *                                      first spike in ms, at the end of the step that reaches threshold)
 *
 * rule: 0 additive (f+ = 1, f- = alpha, the weight clipped to [0, 1]), 1 multiplicative (f+ = 1 - w,
 * f- = alpha w). start: "u" every plastic weight drawn uniformly from [0, 1), "1" every one at 1, "h" every one at
 * 0.5. Synapse 0 is held at 0.5 throughout (the paper's fixed synapse, for chi); synapses 1..999 are plastic when
 * plastic is 1.
 *
 * Each 0.1 ms step: the arrivals (a Poisson count of the population's spikes, each given to a synapse drawn
 * uniformly, which is the superposition of independent Poisson trains), each adding gs w to the conductance g and
 * then, at a plastic synapse, depressing it by lambda f-(w) M, M the postsynaptic trace, and raising its own trace
 * P by 1; then the membrane, tau_m dV/dt = -V - g (V - V_s), by exponential Euler with the step's g; then, at
 * V >= 1, the spike: V reset to 0, every plastic synapse raised by lambda f+(w) P, M raised by 1; then g and M decay
 * by one step. P decays lazily, from the step it was last brought up to date. All pairs count (traces).
 *
 * In the measurement window (the last meas_s seconds), every snap_steps steps the plastic weights go into a
 * histogram of NBIN bins over [0, 1] (the halves of the window into two more); the sums for the cross-correlation
 * of input and output (S+ = the traces P at output spikes, S- = the trace M at arrivals) are kept for synapse 0
 * and pooled over the plastic synapses. Every window_steps steps of the whole run the mean plastic weight and the
 * output rate are printed. Histograms go to out_prefix.hist (three columns), the final weights to out_prefix.w.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 1000
#define DT 0.1              /* ms */
#define TAU_M 20.0
#define TAU_S 5.0
#define V_S 5.0
#define V_TH 1.0
#define V_RESET 0.0
#define TAU 10.0            /* the rule's filter K(t) = exp(-t / TAU) */
#define LAMBDA 0.005
#define ALPHA 1.05
#define W_FIXED 0.5
#define NBIN 10000

static uint64_t s[4];

static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }

static uint64_t next64(void) {   /* xoshiro256** */
    uint64_t r = rotl(s[1] * 5, 7) * 9, t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return r;
}

static double unif(void) { return (double)(next64() >> 11) * 0x1.0p-53; }   /* [0, 1) */

static int below(int m) { return (int)(unif() * m); }

static int poisson(double lam, double emlam) {   /* inversion; lam is small */
    double u = unif(), p = emlam, c = p;
    int k = 0;
    while (u >= c && k < 1000) { k++; p *= lam / k; c += p; }
    return k;
}

static double w[N];          /* weights, in units of gs */
static double P[N];          /* presynaptic traces */
static long last[N];         /* the step each trace was last brought up to date */
static long hist[3][NBIN];   /* the window, its first half, its second half */

static double fminus(int rule, double x) { return rule ? ALPHA * x : ALPHA; }
static double fplus(int rule, double x) { return rule ? 1.0 - x : 1.0; }

static int do_run(int argc, char **argv) {
    if (argc < 16) { fprintf(stderr, "run: arguments\n"); return 2; }
    for (int i = 0; i < 4; i++) s[i] = strtoull(argv[2 + i], NULL, 16);
    int rule = atoi(argv[6]);
    double rate = atof(argv[7]), gs = atof(argv[8]), warm = atof(argv[9]), meas = atof(argv[10]);
    const char *start = argv[11];
    int plastic = atoi(argv[12]);
    long snap = atol(argv[13]), window = atol(argv[14]);
    const char *prefix = argv[15];
    w[0] = W_FIXED;
    for (int a = 1; a < N; a++) {
        if (strcmp(start, "u") == 0) w[a] = unif();
        else if (strcmp(start, "1") == 0) w[a] = 1.0;
        else if (strcmp(start, "h") == 0) w[a] = 0.5;
        else { fprintf(stderr, "start: u, 1 or h\n"); return 2; }
    }
    for (int a = 0; a < N; a++) { P[a] = 0.0; last[a] = 0; }
    memset(hist, 0, sizeof hist);
    long warm_steps = (long)llround(warm / (DT * 1e-3)), meas_steps = (long)llround(meas / (DT * 1e-3));
    long total = warm_steps + meas_steps;
    long nsnap = meas_steps / snap;
    double lam = N * rate * DT * 1e-3, emlam = exp(-lam);
    double dec_s = exp(-DT / TAU_S), dec_k = exp(-DT / TAU);
    double v = V_RESET, g = 0.0, M = 0.0;
    long post_n = 0, pre_n = 0, pre0 = 0, pre_pl = 0, snaps = 0;
    double g_sum = 0.0, splus0 = 0.0, sminus0 = 0.0, spluspool = 0.0, sminuspool = 0.0;
    long double wsum = 0.0L, wss = 0.0L;
    long win_spikes = 0;
    printf("wmean_window=");
    for (long n = 0; n < total; n++) {
        int measuring = n >= warm_steps;
        int k = poisson(lam, emlam);
        for (int j = 0; j < k; j++) {
            int a = below(N);
            g += gs * w[a];
            if (measuring) { pre_n++; if (a == 0) pre0++; else pre_pl++; }
            if (!plastic) continue;
            if (a == 0) {
                if (measuring) sminus0 += M;
            } else {
                w[a] -= LAMBDA * fminus(rule, w[a]) * M;
                if (w[a] < 0.0) w[a] = 0.0;
                if (measuring) sminuspool += M;
            }
            P[a] = P[a] * exp(-(double)(n - last[a]) * DT / TAU) + 1.0;
            last[a] = n;
        }
        double G = 1.0 + g;
        double vinf = g * V_S / G;
        v = vinf + (v - vinf) * exp(-DT * G / TAU_M);
        if (measuring) g_sum += g;
        if (v >= V_TH) {
            v = V_RESET;
            win_spikes++;
            if (measuring) post_n++;
            if (plastic) {
                M += 1.0;
                for (int a = 0; a < N; a++) {
                    double p = P[a] * exp(-(double)(n - last[a]) * DT / TAU);
                    P[a] = p; last[a] = n;
                    if (a == 0) { if (measuring) splus0 += p; continue; }
                    w[a] += LAMBDA * fplus(rule, w[a]) * p;
                    if (w[a] > 1.0) w[a] = 1.0;
                    if (measuring) spluspool += p;
                }
            }
        }
        g *= dec_s; M *= dec_k;
        if (measuring && (n + 1 - warm_steps) % snap == 0) {
            int half = snaps < nsnap / 2 ? 1 : 2;
            for (int a = 1; a < N; a++) {
                int b = (int)(w[a] * NBIN);
                if (b >= NBIN) b = NBIN - 1;
                if (b < 0) b = 0;
                hist[0][b]++; hist[half][b]++;
                wsum += w[a]; wss += (long double)w[a] * w[a];
            }
            snaps++;
        }
        if ((n + 1) % window == 0) {
            double m = 0.0;
            for (int a = 1; a < N; a++) m += w[a];
            printf("%s%.9f:%.2f", (n + 1) == window ? "" : ",", m / (N - 1), win_spikes / (window * DT * 1e-3));
            win_spikes = 0;
        }
    }
    printf("\n");
    double T = meas_steps * DT * 1e-3;
    long nw = snaps * (long)(N - 1);
    double wmean = nw ? (double)(wsum / nw) : 0.0;
    double wvar = nw > 1 ? (double)((wss - wsum * wsum / nw) / (nw - 1)) : 0.0;
    printf("post_spikes=%ld\n", post_n);
    printf("rate=%.17g\n", post_n / T);
    printf("pre_spikes=%ld\n", pre_n);
    printf("pre_fixed=%ld\n", pre0);
    printf("pre_plastic=%ld\n", pre_pl);
    printf("g_mean=%.17g\n", g_sum / meas_steps);
    printf("splus_fixed=%.17g\n", splus0);
    printf("sminus_fixed=%.17g\n", sminus0);
    printf("splus_pool=%.17g\n", spluspool);
    printf("sminus_pool=%.17g\n", sminuspool);
    printf("snapshots=%ld\n", snaps);
    printf("w_mean=%.17g\n", wmean);
    printf("w_sd=%.17g\n", sqrt(wvar > 0 ? wvar : 0.0));
    char path[4096];
    snprintf(path, sizeof path, "%s.hist", prefix);
    FILE *f = fopen(path, "w");
    if (!f) { fprintf(stderr, "cannot write %s\n", path); return 2; }
    for (int b = 0; b < NBIN; b++) fprintf(f, "%ld %ld %ld\n", hist[0][b], hist[1][b], hist[2][b]);
    fclose(f);
    snprintf(path, sizeof path, "%s.w", prefix);
    f = fopen(path, "w");
    if (!f) { fprintf(stderr, "cannot write %s\n", path); return 2; }
    for (int a = 0; a < N; a++) fprintf(f, "%.17g\n", w[a]);
    fclose(f);
    return 0;
}

/* One synapse at w: a pre spike at step 1000 and a post spike round(dt_ms / DT) steps later (earlier if dt_ms < 0),
 * the rule applied as in "run" (the arrival before the spike within a step, traces, lazy decay, clipping). */
static int do_pair(int argc, char **argv) {
    if (argc < 5) return 2;
    int rule = atoi(argv[2]);
    double dtms = atof(argv[3]), w0 = atof(argv[4]);
    long npre = 1000, npost = 1000 + (long)llround(dtms / DT);
    double x = w0, Pa = 0.0, M = 0.0, dec_k = exp(-DT / TAU);
    long lastp = 0;
    long end = (npre > npost ? npre : npost) + 1;
    for (long n = 0; n < end; n++) {
        if (n == npre) {
            x -= LAMBDA * fminus(rule, x) * M; if (x < 0.0) x = 0.0;
            Pa = Pa * exp(-(double)(n - lastp) * DT / TAU) + 1.0; lastp = n;
        }
        if (n == npost) {
            M += 1.0;
            double p = Pa * exp(-(double)(n - lastp) * DT / TAU);
            Pa = p; lastp = n;
            x += LAMBDA * fplus(rule, x) * p; if (x > 1.0) x = 1.0;
        }
        M *= dec_k;
    }
    printf("change=%.17g\n", x - w0);
    return 0;
}

static int do_const(int argc, char **argv) {
    if (argc < 3) return 2;
    double g = atof(argv[2]), v = V_RESET;
    for (long n = 0; n < 10000000; n++) {
        double G = 1.0 + g, vinf = g * V_S / G;
        v = vinf + (v - vinf) * exp(-DT * G / TAU_M);
        if (v >= V_TH) { printf("t_first_ms=%.17g\n", (n + 1) * DT); return 0; }
    }
    printf("t_first_ms=inf\n");
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: rubin run|pair|const ...\n"); return 2; }
    if (strcmp(argv[1], "run") == 0) return do_run(argc, argv);
    if (strcmp(argv[1], "pair") == 0) return do_pair(argc, argv);
    if (strcmp(argv[1], "const") == 0) return do_const(argc, argv);
    fprintf(stderr, "unknown mode %s\n", argv[1]);
    return 2;
}
