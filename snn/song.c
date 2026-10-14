/* Song, Miller & Abbott (2000): one integrate-and-fire neuron, 1000 excitatory synapses under additive STDP and 200
 * fixed inhibitory ones, driven by independent Poisson inputs. The rules are in snn/song.py; this is its simulator.
 *
 * Usage:
 *   song run    w0 w1 w2 w3 rate_hz warm_s meas_s plastic weights_in|- weights_out|-
 *   song pair   dt_ms           (one synapse, one pre and one post spike dt_ms apart, pre minus post; prints the change)
 *
 * "run" starts from the weights read from weights_in (one per line, in units of gmax), or all at gmax if "-"; it runs
 * warm_s seconds and then meas_s seconds, measuring only in the second. It prints key=value lines and writes the final
 * weights to weights_out.
 *
 * Each 0.1 ms step: inhibitory arrivals (a Poisson count, each adding gin_peak), excitatory arrivals (a Poisson count
 * of the whole population's spikes, each given to a synapse drawn uniformly, which is the superposition of independent
 * Poisson trains), each adding the synapse's peak conductance to gex and then, if plastic, depressing it by M gmax and
 * raising its trace P by A+; then the membrane by exponential Euler with the step's conductances; then, at threshold,
 * the spike: reset, M lowered by A-, every synapse raised by P gmax (clipped at gmax); then the conductances and M
 * decay by one step. P decays lazily, from the step it was last touched.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NE 1000
#define NI 200
#define DT 0.1             /* ms */
#define TAU_M 20.0
#define V_REST (-70.0)
#define E_EX 0.0
#define E_IN (-70.0)
#define V_TH (-54.0)
#define V_RESET (-60.0)
#define TAU_EX 5.0
#define TAU_IN 5.0
#define GIN_PEAK 0.05
#define GMAX 0.015
#define TAU_P 20.0
#define TAU_M_STDP 20.0
#define A_PLUS 0.005
#define A_MINUS (1.05 * 0.005)
#define RATE_IN 10.0       /* Hz, the inhibitory inputs */
#define WIN 500            /* steps: the correlogram's half-width, 50 ms */
#define NBIN 100           /* 1 ms bins from -50 to +50 ms */

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

static double g[NE];         /* peak conductances, in units of the leak */
static double P[NE];         /* potentiation traces */
static long last[NE];        /* the step each trace was last brought up to date */

static int do_run(int argc, char **argv) {
    if (argc < 12) { fprintf(stderr, "run: arguments\n"); return 2; }
    for (int i = 0; i < 4; i++) s[i] = strtoull(argv[2 + i], NULL, 16);
    double rate = atof(argv[6]), warm = atof(argv[7]), meas = atof(argv[8]);
    int plastic = atoi(argv[9]);
    const char *win = argv[10], *wout = argv[11];
    if (strcmp(win, "-") == 0) {
        for (int a = 0; a < NE; a++) g[a] = GMAX;
    } else {
        FILE *f = fopen(win, "r");
        if (!f) { fprintf(stderr, "cannot read %s\n", win); return 2; }
        for (int a = 0; a < NE; a++) { double x; if (fscanf(f, "%lf", &x) != 1) { fprintf(stderr, "short weights\n"); return 2; } g[a] = x * GMAX; }
        fclose(f);
    }
    for (int a = 0; a < NE; a++) { P[a] = 0.0; last[a] = 0; }
    long warm_steps = (long)llround(warm / (DT * 1e-3)), meas_steps = (long)llround(meas / (DT * 1e-3));
    long total = warm_steps + meas_steps;
    double lam_in = NI * RATE_IN * DT * 1e-3, em_in = exp(-lam_in);
    double lam_ex = NE * rate * DT * 1e-3, em_ex = exp(-lam_ex);
    double dec_ex = exp(-DT / TAU_EX), dec_in = exp(-DT / TAU_IN), dec_m = exp(-DT / TAU_M_STDP);
    double v = V_REST, gex = 0.0, gin = 0.0, M = 0.0;
    /* measurement */
    long post_n = 0, isi_n = 0, last_post = -1, pre_n = 0, inh_n = 0;
    double isi_s = 0.0, isi_ss = 0.0, gex_sum = 0.0, gin_sum = 0.0;
    long corr[NBIN];
    memset(corr, 0, sizeof corr);
    static long pre_ring[1 << 16];    /* excitatory arrival steps in the last WIN steps */
    long pre_head = 0, pre_tail = 0;
    static long post_ring[4096];
    long post_head = 0, post_tail = 0;
    long window_spikes = 0, window_steps = 100000;   /* 10 s windows, over the whole run */
    printf("window_s=10\n");
    printf("rates_10s=");
    for (long n = 0; n < total; n++) {
        int measuring = n >= warm_steps;
        int ki = poisson(lam_in, em_in);
        gin += ki * GIN_PEAK;
        int ke = poisson(lam_ex, em_ex);
        for (int j = 0; j < ke; j++) {
            int a = below(NE);
            gex += g[a];
            if (plastic) {
                g[a] += M * GMAX;
                if (g[a] < 0.0) g[a] = 0.0;
                P[a] = P[a] * exp(-(double)(n - last[a]) * DT / TAU_P) + A_PLUS;
                last[a] = n;
            }
            if (measuring) {
                pre_n++;
                pre_ring[pre_head++ & 0xffff] = n;
                for (long q = post_tail; q < post_head; q++) {          /* pre after a recent post */
                    long d = n - post_ring[q & 4095];
                    if (d >= 1 && d <= WIN) corr[50 + (d - 1) / 10]++;
                }
            }
        }
        if (measuring) inh_n += ki;
        double G = 1.0 + gex + gin;
        double vinf = (V_REST + gex * E_EX + gin * E_IN) / G;
        v = vinf + (v - vinf) * exp(-DT * G / TAU_M);
        if (measuring) { gex_sum += gex; gin_sum += gin; }
        if (v >= V_TH) {
            v = V_RESET;
            window_spikes++;
            if (plastic) {
                M -= A_MINUS;
                for (int a = 0; a < NE; a++) {
                    double p = P[a] * exp(-(double)(n - last[a]) * DT / TAU_P);
                    P[a] = p; last[a] = n;
                    g[a] += p * GMAX;
                    if (g[a] > GMAX) g[a] = GMAX;
                }
            }
            if (measuring) {
                post_n++;
                if (last_post >= 0) { double isi = (n - last_post) * DT; isi_s += isi; isi_ss += isi * isi; isi_n++; }
                last_post = n;
                while (pre_tail < pre_head && n - pre_ring[pre_tail & 0xffff] > WIN - 1) pre_tail++;
                for (long q = pre_tail; q < pre_head; q++) {             /* pre before (or in the step of) the post */
                    long d = pre_ring[q & 0xffff] - n;                   /* -(WIN - 1) .. 0 */
                    corr[49 - (-d) / 10]++;
                }
                post_ring[post_head++ & 4095] = n;
            }
        }
        if (measuring) {
            while (post_tail < post_head && n - post_ring[post_tail & 4095] >= WIN) post_tail++;
            while (pre_tail < pre_head && n - pre_ring[pre_tail & 0xffff] > WIN - 1) pre_tail++;
        }
        gex *= dec_ex; gin *= dec_in; M *= dec_m;
        if ((n + 1) % window_steps == 0) { printf("%s%.1f", (n + 1) == window_steps ? "" : ",", window_spikes / 10.0); window_spikes = 0; }
    }
    printf("\n");
    double T = meas_steps * DT * 1e-3;
    double mean_isi = isi_n ? isi_s / isi_n : 0.0;
    double var = isi_n > 1 ? (isi_ss - isi_n * mean_isi * mean_isi) / (isi_n - 1) : 0.0;
    printf("post_spikes=%ld\n", post_n);
    printf("rate=%.17g\n", post_n / T);
    printf("cv=%.17g\n", (isi_n > 1 && mean_isi > 0) ? sqrt(var > 0 ? var : 0) / mean_isi : 0.0);
    printf("gex_mean=%.17g\n", gex_sum / meas_steps);
    printf("gin_mean=%.17g\n", gin_sum / meas_steps);
    printf("pre_spikes=%ld\n", pre_n);
    printf("inh_spikes=%ld\n", inh_n);
    printf("corr=");
    for (int b = 0; b < NBIN; b++) printf("%s%ld", b ? "," : "", corr[b]);
    printf("\n");
    if (strcmp(wout, "-") != 0) {
        FILE *f = fopen(wout, "w");
        if (!f) { fprintf(stderr, "cannot write %s\n", wout); return 2; }
        for (int a = 0; a < NE; a++) fprintf(f, "%.17g\n", g[a] / GMAX);
        fclose(f);
    }
    return 0;
}

/* One synapse at gmax/2: a pre spike at step 1000 and a post spike dt_ms later (pre minus post = -dt_ms) or earlier;
 * the rule applied as in "run" (traces, lazy decay, clipping), the change printed in units of gmax. */
static int do_pair(int argc, char **argv) {
    if (argc < 3) return 2;
    double dtms = atof(argv[2]);        /* pre minus post, in ms */
    long npre = 1000, npost = 1000 - (long)llround(dtms / DT);
    double w = 0.5 * GMAX, Pa = 0.0, M = 0.0, dec_m = exp(-DT / TAU_M_STDP);
    long lastp = 0;
    long end = (npre > npost ? npre : npost) + 1;
    for (long n = 0; n < end; n++) {
        if (n == npre) {
            w += M * GMAX; if (w < 0) w = 0;
            Pa = Pa * exp(-(double)(n - lastp) * DT / TAU_P) + A_PLUS; lastp = n;
        }
        if (n == npost) {
            M -= A_MINUS;
            double p = Pa * exp(-(double)(n - lastp) * DT / TAU_P);
            Pa = p; lastp = n;
            w += p * GMAX; if (w > GMAX) w = GMAX;
        }
        M *= dec_m;
    }
    printf("change=%.17g\n", (w - 0.5 * GMAX) / GMAX);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: song run|pair ...\n"); return 2; }
    if (strcmp(argv[1], "run") == 0) return do_run(argc, argv);
    if (strcmp(argv[1], "pair") == 0) return do_pair(argc, argv);
    fprintf(stderr, "unknown mode %s\n", argv[1]);
    return 2;
}
