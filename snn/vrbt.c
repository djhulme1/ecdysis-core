/* van Rossum, Bi & Turrigiano (2000): one leaky integrate-and-fire neuron, 100 excitatory synapses under the paper's
 * STDP rule and 25 fixed inhibitory ones, driven by independent Poisson inputs. The rules are in snn/vrbt.py; this is
 * its simulator.
 *
 * Usage:
 *   vrbt run  w0 w1 w2 w3 start dur_s from_s sample_s ginh_pS cd sigma plastic weights_out|-
 *       start: "uniform" (each weight drawn uniformly from [0, 2 cp/cd0), cd0 = 0.003), "file:PATH" (100 weights, one a
 *       line) or a number of pS (every weight at it); dur_s seconds are simulated; snapshots of every weight are taken every sample_s seconds after from_s,
 *       into two halves of the window (from_s, dur_s]; ginh_pS is each inhibitory synapse's conductance; cd the
 *       depression constant and sigma the noise's standard deviation; plastic 0 holds every weight.
 *   vrbt pair w_pS sigma events
 *       one synapse at w_pS, a scripted sequence of events "pre:STEP" and "post:STEP" (comma-separated, in order of
 *       step), the rule applied as in "run"; prints the final weight.
 *
 * Units: conductances in pS, entering the membrane in units of the leak (1/R = 10 nS = 10,000 pS).
 *
 * Each 0.1 ms step: inhibitory arrivals (a Poisson count, each adding ginh); excitatory arrivals (a Poisson count of the
 * whole population's spikes, each given to a synapse drawn uniformly: the superposition of independent Poisson
 * trains), each adding its synapse's weight to gex and then, if plastic, depressing it once for every postsynaptic
 * spike since the synapse's previous arrival (each postsynaptic spike is depressed by the first arrival after it), by
 * (-cd w + nu w) exp(-dt/tau), and queueing the arrival; then the membrane by exponential Euler with the step's
 * conductances; then, at threshold, the spike: reset to rest, and every queued arrival potentiates its synapse once,
 * by (cp + nu w) exp(-dt/tau) (each arrival is potentiated by the first postsynaptic spike after it), and the queues
 * empty; then the conductances decay by one step; then, at the end of a sampling interval inside the window, a
 * snapshot. nu is a fresh Gaussian draw, mean 0 and standard deviation sigma, for every change. An arrival in the step
 * of a postsynaptic spike came before it (dt = 0).
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NE 100
#define NI 25
#define DT 0.1              /* ms */
#define TAU_M 20.0
#define V_REST (-60.0)
#define V_TH (-50.0)
#define E_EX 0.0
#define E_IN (-70.0)
#define TAU_S 5.0           /* both synapse kinds */
#define G_LEAK 10000.0      /* pS: 1 / (100 MOhm) */
#define RATE 20.0           /* Hz, every input */
#define TAU_STDP 20.0       /* ms, potentiation and depression */
#define CP 1.0              /* pS */
#define CD0 0.003
#define PI_ 3.14159265358979323846
#define PEND 64             /* arrivals queued per synapse, the oldest overwritten (their factor is below e^-100) */
#define RING 4096           /* postsynaptic spikes kept for depression */
#define NBINS 10000         /* 0.5 pS bins from 0 to 5000 pS; one more bin for 5000 and above */
#define BIN 0.5
#define SHIFT 333.33333333333331   /* cp / cd0: moments are summed about it */

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

static double gauss(void) {   /* Box-Muller, two fresh uniforms for every draw */
    double u1 = 1.0 - unif(), u2 = unif();
    return sqrt(-2.0 * log(u1)) * cos(2.0 * PI_ * u2);
}

static double w[NE];
static long pend[NE][PEND];
static int pend_n[NE], pend_head[NE];
static long dep_from[NE];        /* the index of the first postsynaptic spike this synapse has not been depressed for */
static long post_step[RING];
static long hist[2][NBINS + 1];
static long double mom[2][4];    /* count, and sums of (w - SHIFT), its square and cube */
static double wmin = 1e300, wmax = -1e300;
static long underflow = 0, pend_over = 0;

static void snapshot(int half) {
    for (int a = 0; a < NE; a++) {
        double x = w[a];
        if (x < 0.0) { underflow++; continue; }
        long b = (long)(x / BIN);
        if (b > NBINS) b = NBINS;
        hist[half][b]++;
        long double d = (long double)x - SHIFT;
        mom[half][0] += 1.0L; mom[half][1] += d; mom[half][2] += d * d; mom[half][3] += d * d * d;
        if (x < wmin) wmin = x;
        if (x > wmax) wmax = x;
    }
}

static int do_run(int argc, char **argv) {
    if (argc < 15) { fprintf(stderr, "run: arguments\n"); return 2; }
    for (int i = 0; i < 4; i++) s[i] = strtoull(argv[2 + i], NULL, 16);
    const char *start = argv[6];
    double dur = atof(argv[7]), from = atof(argv[8]), sample = atof(argv[9]), ginh = atof(argv[10]);
    double cd = atof(argv[11]), sigma = atof(argv[12]);
    int plastic = atoi(argv[13]);
    const char *wout = argv[14];
    if (strcmp(start, "uniform") == 0) {
        for (int a = 0; a < NE; a++) w[a] = unif() * (2.0 * CP / CD0);
    } else if (strncmp(start, "file:", 5) == 0) {
        FILE *f = fopen(start + 5, "r");
        if (!f) { fprintf(stderr, "cannot read %s\n", start + 5); return 2; }
        for (int a = 0; a < NE; a++) if (fscanf(f, "%lf", &w[a]) != 1) { fprintf(stderr, "short start file\n"); return 2; }
        fclose(f);
    } else {
        double x = atof(start);
        for (int a = 0; a < NE; a++) w[a] = x;
    }
    for (int a = 0; a < NE; a++) { pend_n[a] = 0; pend_head[a] = 0; dep_from[a] = 0; }
    long total = (long)llround(dur / (DT * 1e-3)), from_steps = (long)llround(from / (DT * 1e-3));
    long sample_steps = (long)llround(sample / (DT * 1e-3));
    long mid_steps = from_steps + (total - from_steps) / 2;
    double lam_in = NI * RATE * DT * 1e-3, em_in = exp(-lam_in);
    double lam_ex = NE * RATE * DT * 1e-3, em_ex = exp(-lam_ex);
    double dec = exp(-DT / TAU_S), gin_unit = ginh / G_LEAK;
    double v = V_REST, gex = 0.0, gin = 0.0;
    long post_count = 0, post_meas = 0, pre_meas = 0, inh_meas = 0;
    double gex_sum = 0.0, gin_sum = 0.0;
    long steps_meas = 0;
    for (long n = 0; n < total; n++) {
        int measuring = n >= from_steps;
        int ki = poisson(lam_in, em_in);
        gin += ki * gin_unit;
        int ke = poisson(lam_ex, em_ex);
        for (int j = 0; j < ke; j++) {
            int a = below(NE);
            gex += w[a] / G_LEAK;
            if (plastic) {
                if (post_count - dep_from[a] > RING) { fprintf(stderr, "depression ring overflow\n"); return 3; }
                for (long q = dep_from[a]; q < post_count; q++) {
                    double f = exp(-(double)(n - post_step[q % RING]) * DT / TAU_STDP);
                    double nu = sigma * gauss();
                    w[a] += (-cd * w[a] + nu * w[a]) * f;
                }
                dep_from[a] = post_count;
                if (pend_n[a] == PEND) pend_over++;
                pend[a][pend_head[a]] = n;
                pend_head[a] = (pend_head[a] + 1) % PEND;
                if (pend_n[a] < PEND) pend_n[a]++;
            }
            if (measuring) pre_meas++;
        }
        if (measuring) inh_meas += ki;
        double G = 1.0 + gex + gin;
        double vinf = (V_REST + gex * E_EX + gin * E_IN) / G;
        v = vinf + (v - vinf) * exp(-DT * G / TAU_M);
        if (measuring) { gex_sum += gex; gin_sum += gin; steps_meas++; }
        if (v >= V_TH) {
            v = V_REST;
            post_step[post_count % RING] = n;
            post_count++;
            if (measuring) post_meas++;
            if (plastic) {
                for (int a = 0; a < NE; a++) {
                    int k0 = (pend_head[a] - pend_n[a] + PEND) % PEND;   /* oldest first */
                    for (int k = 0; k < pend_n[a]; k++) {
                        long m = pend[a][(k0 + k) % PEND];
                        double f = exp(-(double)(n - m) * DT / TAU_STDP);
                        double nu = sigma * gauss();
                        w[a] += (CP + nu * w[a]) * f;
                    }
                    pend_n[a] = 0;
                }
            }
        }
        gex *= dec; gin *= dec;
        if (n + 1 > from_steps && (n + 1 - from_steps) % sample_steps == 0) snapshot(n + 1 <= mid_steps ? 0 : 1);
    }
    double T = (total - from_steps) * DT * 1e-3;
    printf("rate=%.17g\n", T > 0 ? post_meas / T : 0.0);
    printf("post_spikes=%ld\n", post_meas);
    printf("pre_arrivals=%ld\n", pre_meas);
    printf("inh_arrivals=%ld\n", inh_meas);
    printf("gex_mean=%.17g\n", steps_meas ? gex_sum / steps_meas : 0.0);
    printf("gin_mean=%.17g\n", steps_meas ? gin_sum / steps_meas : 0.0);
    printf("wmin=%.17g\nwmax=%.17g\n", wmin, wmax);
    printf("underflow=%ld\npend_over=%ld\n", underflow, pend_over);
    for (int h = 0; h < 2; h++) {
        printf("mom%d=%.17Lg,%.17Lg,%.17Lg,%.17Lg\n", h, mom[h][0], mom[h][1], mom[h][2], mom[h][3]);
        printf("hist%d=", h);
        int first = 1;
        for (long b = 0; b <= NBINS; b++) if (hist[h][b]) { printf("%s%ld:%ld", first ? "" : ",", b, hist[h][b]); first = 0; }
        printf("\n");
    }
    if (strcmp(wout, "-") != 0) {
        FILE *f = fopen(wout, "w");
        if (!f) { fprintf(stderr, "cannot write %s\n", wout); return 2; }
        for (int a = 0; a < NE; a++) fprintf(f, "%.17g\n", w[a]);
        fclose(f);
    }
    return 0;
}

/* One synapse at w_pS and a scripted list of events, applied with the rule of "run" (fixed seed for the noise). */
static int do_pair(int argc, char **argv) {
    if (argc < 5) return 2;
    double x = atof(argv[2]), sigma = atof(argv[3]);
    s[0] = 1; s[1] = 2; s[2] = 3; s[3] = 4;
    long posts[RING], npost = 0, from = 0, queue[PEND];
    int nq = 0;
    char *list = strdup(argv[4]);
    for (char *tok = strtok(list, ","); tok; tok = strtok(NULL, ",")) {
        char kind[8];
        long n;
        if (sscanf(tok, "%7[a-z]:%ld", kind, &n) != 2) { fprintf(stderr, "bad event %s\n", tok); return 2; }
        if (strcmp(kind, "pre") == 0) {
            for (long q = from; q < npost; q++) {
                double f = exp(-(double)(n - posts[q]) * DT / TAU_STDP);
                double nu = sigma * gauss();
                x += (-CD0 * x + nu * x) * f;
            }
            from = npost;
            if (nq < PEND) queue[nq++] = n;
        } else if (strcmp(kind, "post") == 0) {
            for (int k = 0; k < nq; k++) {
                double f = exp(-(double)(n - queue[k]) * DT / TAU_STDP);
                double nu = sigma * gauss();
                x += (CP + nu * x) * f;
            }
            nq = 0;
            posts[npost++] = n;
        } else { fprintf(stderr, "bad kind %s\n", kind); return 2; }
    }
    free(list);
    printf("w=%.17g\n", x);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: vrbt run|pair ...\n"); return 2; }
    if (strcmp(argv[1], "run") == 0) return do_run(argc, argv);
    if (strcmp(argv[1], "pair") == 0) return do_pair(argc, argv);
    fprintf(stderr, "unknown mode %s\n", argv[1]);
    return 2;
}
