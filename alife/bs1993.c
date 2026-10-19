/* Bak & Sneppen (1993): species on a ring (or a square lattice) with random barriers; at each step the lowest
 * barrier and its neighbours' barriers are replaced by new random numbers. The rules are in alife/bs1993.py; this is
 * its simulator.
 *
 * Usage:
 *   bs1993 run w0 w1 w2 w3 dim L mode start warm meas snaps seg out_prefix f0_1 [f0_2 ...]
 *
 * dim 1: N = L species on a ring, each with two neighbours; dim 2: N = L x L on a torus, four neighbours. mode
 * "n": the minimum and its neighbours get new barriers (the paper's rule); "s": the minimum alone (a planted fault,
 * no interaction). start "u": every barrier uniform on [0, 1); "h": uniform on [0.9, 1). warm and meas are numbers of
 * steps (one step = one mutation, the paper's unit of time). The minimum is found with a tournament tree (the lowest
 * index on a tie, as a plain scan would find it).
 *
 * In the measurement window (the last meas steps): snaps snapshots of all barriers at equal intervals, histogrammed
 * on NBIN bins of [0, 1) (the window's halves in two more columns); every selected minimum into a histogram on NBIN
 * bins, and the largest; the ring distance between successive minima (dim 1); the waiting time between successive
 * minima in each block of seg consecutive sites (dim 1; blocks fully inside the ring only); and for each threshold
 * f0, the avalanches: maximal runs of consecutive steps whose selected minimum is below f0, their sizes (the run
 * lengths, followed from the run's start even if it began before the window) histogrammed on 100 logarithmic bins
 * per decade; a run still open when the window ends is not counted. Sizes and waits use LBIN bins (bin
 * floor(100 log10 x)).
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NBIN 10000
#define LBIN 1300
#define MAXF 16

static uint64_t s[4];

static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }

static uint64_t next64(void) {   /* xoshiro256** */
    uint64_t r = rotl(s[1] * 5, 7) * 9, t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return r;
}

static double unif(void) { return (double)(next64() >> 11) * 0x1.0p-53; }   /* [0, 1) */

static int N, P;
static double *b;      /* barriers */
static double *tv;     /* tournament tree over P leaves: the lowest barrier below each node */
static int *ti;        /* and its site; a tie goes to the left child, whose sites are the lower, so the lowest
                          site wins, as a plain scan would find it; leaves past N hold 2, which never wins */

static void build(void) {
    for (int k = 0; k < P; k++) { tv[P + k] = k < N ? b[k] : 2.0; ti[P + k] = k; }
    for (int k = P - 1; k >= 1; k--) {
        int l = 2 * k, r = 2 * k + 1, w = tv[r] < tv[l] ? r : l;
        tv[k] = tv[w]; ti[k] = ti[w];
    }
}

static void fix(int i) {   /* site i's barrier changed: bring its ancestors up to date, stopping where none changes */
    int k = P + i;
    tv[k] = b[i];
    k >>= 1;
    while (k >= 1) {
        int l = 2 * k, r = 2 * k + 1, w = tv[r] < tv[l] ? r : l;
        if (tv[k] == tv[w] && ti[k] == ti[w]) break;
        tv[k] = tv[w]; ti[k] = ti[w];
        k >>= 1;
    }
}

#define LTAB (1 << 20)
static short *ltab;    /* floor(100 log10 x) for x < LTAB, computed once */

static int lbin(long x) {   /* floor(100 log10 x) for x >= 1 */
    int k = x < LTAB ? ltab[x] : (int)floor(100.0 * log10((double)x));
    if (k < 0) k = 0;
    if (k >= LBIN) k = LBIN - 1;
    return k;
}

static int write_counts(const char *prefix, const char *ext, long *v, int n) {
    char path[4096];
    snprintf(path, sizeof path, "%s.%s", prefix, ext);
    FILE *f = fopen(path, "w");
    if (!f) { fprintf(stderr, "cannot write %s\n", path); return 2; }
    for (int k = 0; k < n; k++) fprintf(f, "%ld\n", v[k]);
    fclose(f);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 16 || strcmp(argv[1], "run") != 0) {
        fprintf(stderr, "usage: bs1993 run w0 w1 w2 w3 dim L mode start warm meas snaps seg out_prefix f0...\n");
        return 2;
    }
    for (int i = 0; i < 4; i++) s[i] = strtoull(argv[2 + i], NULL, 16);
    int dim = atoi(argv[6]), L = atoi(argv[7]);
    const char *mode = argv[8], *start = argv[9];
    long warm = atol(argv[10]), meas = atol(argv[11]), snaps = atol(argv[12]);
    int seg = atoi(argv[13]);
    const char *prefix = argv[14];
    int nf = argc - 15;
    if (nf > MAXF) { fprintf(stderr, "too many thresholds\n"); return 2; }
    double f0[MAXF];
    for (int j = 0; j < nf; j++) f0[j] = atof(argv[15 + j]);
    if (dim != 1 && dim != 2) { fprintf(stderr, "dim 1 or 2\n"); return 2; }
    int self_only = strcmp(mode, "s") == 0;
    if (!self_only && strcmp(mode, "n") != 0) { fprintf(stderr, "mode n or s\n"); return 2; }
    N = dim == 1 ? L : L * L;
    P = 1; while (P < N) P <<= 1;
    b = malloc(sizeof(double) * N);
    tv = malloc(sizeof(double) * 2 * P);
    ti = malloc(sizeof(int) * 2 * P);
    ltab = malloc(sizeof(short) * LTAB);
    if (!tv || !ti || !ltab) { fprintf(stderr, "memory\n"); return 2; }
    ltab[0] = 0;
    for (long x = 1; x < LTAB; x++) ltab[x] = (short)floor(100.0 * log10((double)x));
    long *bh = calloc(3 * NBIN, sizeof(long)), *mh = calloc(NBIN, sizeof(long));
    long *cx = calloc(N / 2 + 1, sizeof(long)), *wt = calloc(LBIN, sizeof(long));
    long *av = calloc((size_t)MAXF * LBIN, sizeof(long)), run[MAXF], nav[MAXF];
    int nseg = dim == 1 && seg > 0 ? N / seg : 0;
    long *lastseg = malloc(sizeof(long) * (nseg > 0 ? nseg : 1));
    if (!b || !bh || !mh || !cx || !wt || !av || !lastseg) { fprintf(stderr, "memory\n"); return 2; }
    for (int i = 0; i < N; i++) {
        if (strcmp(start, "u") == 0) b[i] = unif();
        else if (strcmp(start, "h") == 0) b[i] = 0.9 + 0.1 * unif();
        else { fprintf(stderr, "start u or h\n"); return 2; }
    }
    build();
    for (int j = 0; j < nf; j++) { run[j] = 0; nav[j] = 0; }
    for (int k = 0; k < nseg; k++) lastseg[k] = -1;
    long total = warm + meas, snap_every = snaps > 0 ? meas / snaps : 0, nsnap = 0;
    double maxmin = -1.0;
    long prev = -1, wsum = 0;
    double minsum = 0.0;
    for (long n = 0; n < total; n++) {
        int i = ti[1];
        double m = b[i];
        for (int j = 0; j < nf; j++) {   /* runs are followed from the start; one ending in the window is counted */
            if (m < f0[j]) run[j]++;
            else if (run[j] > 0) {
                if (n >= warm) { av[(size_t)j * LBIN + lbin(run[j])]++; nav[j]++; }
                run[j] = 0;
            }
        }
        if (n >= warm) {
            int bb = (int)(m * NBIN); if (bb >= NBIN) bb = NBIN - 1;
            mh[bb]++;
            minsum += m;
            if (m > maxmin) maxmin = m;
            if (dim == 1) {
                if (prev >= 0) {
                    long d = labs((long)i - prev); if (d > N - d) d = N - d;
                    cx[d]++;
                }
                if (nseg > 0 && i < nseg * seg) {
                    int k = i / seg;
                    if (lastseg[k] >= 0) { wt[lbin(n - lastseg[k])]++; wsum++; }
                    lastseg[k] = n;
                }
            }
            prev = i;
        }
        b[i] = unif(); fix(i);
        if (!self_only) {
            if (dim == 1) {
                int l = i == 0 ? N - 1 : i - 1, r = i == N - 1 ? 0 : i + 1;
                b[l] = unif(); fix(l);
                b[r] = unif(); fix(r);
            } else {
                int x = i % L, y = i / L;
                int nb[4] = {y * L + (x + L - 1) % L, y * L + (x + 1) % L, ((y + L - 1) % L) * L + x,
                             ((y + 1) % L) * L + x};
                for (int q = 0; q < 4; q++) { b[nb[q]] = unif(); fix(nb[q]); }
            }
        }
        if (n >= warm && snap_every > 0 && (n + 1 - warm) % snap_every == 0 && nsnap < snaps) {
            int half = nsnap < snaps / 2 ? 1 : 2;
            for (int q = 0; q < N; q++) {
                int bb = (int)(b[q] * NBIN); if (bb >= NBIN) bb = NBIN - 1;
                bh[bb]++; bh[half * NBIN + bb]++;
            }
            nsnap++;
        }
    }
    /* runs still open at the end of the window are not counted (their sizes are unknown) */
    printf("N=%d\n", N);
    printf("steps=%ld\n", meas);
    printf("snapshots=%ld\n", nsnap);
    printf("max_min=%.17g\n", maxmin);
    printf("mean_min=%.17g\n", meas > 0 ? minsum / meas : 0.0);
    printf("waits=%ld\n", wsum);
    printf("avalanches=");
    for (int j = 0; j < nf; j++) printf("%s%ld", j ? "," : "", nav[j]);
    printf("\n");
    printf("open_runs=");
    for (int j = 0; j < nf; j++) printf("%s%ld", j ? "," : "", run[j]);
    printf("\n");
    char path[4096];
    snprintf(path, sizeof path, "%s.bhist", prefix);
    FILE *f = fopen(path, "w");
    if (!f) { fprintf(stderr, "cannot write %s\n", path); return 2; }
    for (int k = 0; k < NBIN; k++) fprintf(f, "%ld %ld %ld\n", bh[k], bh[NBIN + k], bh[2 * NBIN + k]);
    fclose(f);
    if (write_counts(prefix, "mhist", mh, NBIN)) return 2;
    if (write_counts(prefix, "cx", cx, N / 2 + 1)) return 2;
    if (write_counts(prefix, "wait", wt, LBIN)) return 2;
    snprintf(path, sizeof path, "%s.aval", prefix);
    f = fopen(path, "w");
    if (!f) { fprintf(stderr, "cannot write %s\n", path); return 2; }
    for (int k = 0; k < LBIN; k++) {
        for (int j = 0; j < nf; j++) fprintf(f, "%s%ld", j ? " " : "", av[(size_t)j * LBIN + k]);
        fprintf(f, "\n");
    }
    fclose(f);
    snprintf(path, sizeof path, "%s.final", prefix);
    f = fopen(path, "w");
    if (!f) { fprintf(stderr, "cannot write %s\n", path); return 2; }
    for (int q = 0; q < N; q++) fprintf(f, "%.17g\n", b[q]);
    fclose(f);
    return 0;
}
