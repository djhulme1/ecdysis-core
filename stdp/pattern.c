/* Masquelier, Guyonneau & Thorpe (2008): STDP finds the start of a repeating pattern in continuous spike trains.

   Imago's laboratory (https://ecdysis.me/a/Imago); the rules are in stdp/pattern.py's docstring, which drives this.

   Usage: pattern SEED N_AFFERENTS N_PATTERN BASE_SECONDS REPEATS W0 STDP DUMP OUT
     SEED          64-bit seed of this run (decimal)
     N_AFFERENTS   afferents (2,000 in the paper); the first N_PATTERN take part in the pattern (1,000)
     BASE_SECONDS  length of the generated train (150 s), pasted REPEATS times (3, so 450 s)
     W0            initial weight of every synapse (0.475)
     STDP          1 to learn, 0 to hold the weights fixed
     DUMP          a file to write the events and the post-synaptic spikes to (a test's reference), or "-"
     OUT           the run's record (text, one "key value" per line)

   Times are kept in microseconds (integers) for the inputs; the neuron is simulated event by event in double
   precision. Every random number comes from xoshiro256** seeded by splitmix64 from SEED. */

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---------------------------------------------------------------- random numbers */
static uint64_t S[4];
static uint64_t splitmix(uint64_t *x) {
    uint64_t z = (*x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
static uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t next(void) {
    uint64_t r = rotl(S[1] * 5, 7) * 9, t = S[1] << 17;
    S[2] ^= S[0]; S[3] ^= S[1]; S[1] ^= S[2]; S[0] ^= S[3]; S[2] ^= t; S[3] = rotl(S[3], 45);
    return r;
}
static double unif(void) { return (next() >> 11) * 0x1.0p-53; }            /* [0, 1) */
static double gauss(void) {                                                   /* Box-Muller, one value per call */
    double u = unif(), v = unif();
    if (u < 1e-300) u = 1e-300;
    return sqrt(-2.0 * log(u)) * cos(2.0 * M_PI * v);
}

/* ---------------------------------------------------------------- the model's constants (pattern.py rule 2) */
#define DT_MS 1                    /* the generator's time step */
#define R_MAX 90.0                 /* Hz */
#define S_MAX (90.0 / 0.050)       /* Hz/s: 0 to 90 Hz in 50 ms */
#define S_STEP (S_MAX / 5.0)       /* the largest random change of s in one step (rule 2's reading) */
#define SILENCE_MS 50              /* a spike is forced after more than 50 ms of silence */
#define SECTION_MS 50              /* the pattern's length */
#define SPONT_HZ 10.0
#define JITTER_MS 1.0
#define TAU_M 10.0                 /* ms */
#define TAU_S 2.5
#define THRESHOLD 500.0
#define K1 2.0
#define K2 4.0
#define CUT (7.0 * TAU_M)          /* kernels set to zero beyond 7 tau_m */
#define REFRACTORY 1.0
#define TAU_PLUS 16.8
#define TAU_MINUS 33.7
#define A_PLUS 0.03125
#define A_MINUS (0.85 * A_PLUS)

static void die(const char *m) { fprintf(stderr, "pattern: %s\n", m); exit(2); }

/* ---------------------------------------------------------------- events: (time in us) << 12 | afferent */
typedef struct { uint64_t *k; size_t n, cap; } Events;
static void push(Events *e, int64_t t_us, int aff) {
    if (t_us < 0) t_us = 0;
    if (e->n == e->cap) {
        e->cap = e->cap ? e->cap * 2 : (1 << 20);
        e->k = realloc(e->k, e->cap * sizeof(uint64_t));
        if (!e->k) die("out of memory");
    }
    e->k[e->n++] = ((uint64_t)t_us << 12) | (uint64_t)aff;
}
static void radix(uint64_t *a, size_t n) {
    uint64_t *b = malloc(n * sizeof(uint64_t));
    if (!b) die("out of memory");
    for (int pass = 0; pass < 8; pass++) {
        size_t cnt[257] = {0};
        int sh = pass * 8;
        for (size_t i = 0; i < n; i++) cnt[((a[i] >> sh) & 255) + 1]++;
        for (int i = 0; i < 256; i++) cnt[i + 1] += cnt[i];
        for (size_t i = 0; i < n; i++) b[cnt[(a[i] >> sh) & 255]++] = a[i];
        uint64_t *t = a; a = b; b = t;
    }
    free(b);   /* eight passes: the sorted keys are back in the original array */
}

int main(int argc, char **argv) {
    if (argc != 10) die("usage: pattern SEED N_AFFERENTS N_PATTERN BASE_SECONDS REPEATS W0 STDP DUMP OUT");
    uint64_t seed = strtoull(argv[1], NULL, 10);
    int N = atoi(argv[2]), NP = atoi(argv[3]), BASE = atoi(argv[4]), REP = atoi(argv[5]);
    double W0 = atof(argv[6]);
    int stdp = atoi(argv[7]);
    const char *dump = argv[8], *out = argv[9];
    if (N < 1 || N > 4095 || NP < 0 || NP > N || BASE < 1 || REP < 1) die("bad arguments");
    uint64_t x = seed;
    for (int i = 0; i < 4; i++) S[i] = splitmix(&x);

    /* 1. the original trains, on a 1 ms grid (rule 1) */
    int steps = BASE * 1000;
    int nsec = steps / SECTION_MS;
    Events orig = {0};
    long long count_orig = 0, count_forced = 0;
    for (int a = 0; a < N; a++) {
        double r = unif() * R_MAX, s = (2.0 * unif() - 1.0) * S_MAX;
        int silent = 0;
        for (int t = 0; t < steps; t++) {
            int spike = unif() < r * DT_MS * 1e-3;
            if (!spike && silent >= SILENCE_MS) { spike = 1; count_forced++; }
            if (spike) { push(&orig, (int64_t)t * 1000, a); silent = 0; count_orig++; } else silent++;
            r += s * DT_MS * 1e-3;
            if (r < 0) r = 0;
            if (r > R_MAX) r = R_MAX;
            s += (2.0 * unif() - 1.0) * S_STEP;
            if (s < -S_MAX) s = -S_MAX;
            if (s > S_MAX) s = S_MAX;
        }
    }
    radix(orig.k, orig.n);

    /* 2. the pattern: one 50 ms section of the first NP afferents, pasted with jitter into a quarter of the sections,
       no two consecutive (rule 1) */
    int npaste = nsec / 4;
    int src = (int)(unif() * nsec);
    int slots = nsec - (npaste - 1);
    int *pick = malloc(sizeof(int) * slots), *sel = malloc(sizeof(int) * npaste);
    for (int i = 0; i < slots; i++) pick[i] = i;
    for (int i = 0; i < npaste; i++) {              /* a uniform npaste-subset of the slots, partial Fisher-Yates */
        int j = i + (int)(unif() * (slots - i));
        int t = pick[i]; pick[i] = pick[j]; pick[j] = t;
    }
    for (int i = 0; i < npaste; i++) sel[i] = pick[i];
    for (int i = 1; i < npaste; i++) {               /* sort the chosen slots */
        int v = sel[i], j = i - 1;
        while (j >= 0 && sel[j] > v) { sel[j + 1] = sel[j]; j--; }
        sel[j + 1] = v;
    }
    for (int i = 0; i < npaste; i++) sel[i] += i;    /* slots to sections: none consecutive, uniformly */
    char *pasted = calloc(nsec, 1);
    for (int i = 0; i < npaste; i++) pasted[sel[i]] = 1;
    /* the pattern's spikes: the source section's spikes of the first NP afferents, relative to its start (us) */
    size_t pn = 0, pcap = 1024;
    int64_t *pt = malloc(sizeof(int64_t) * pcap);
    int *pa = malloc(sizeof(int) * pcap);
    for (size_t i = 0; i < orig.n; i++) {
        int64_t t = (int64_t)(orig.k[i] >> 12);
        int a = (int)(orig.k[i] & 4095);
        if (a < NP && t / 1000 / SECTION_MS == src) {
            if (pn == pcap) { pcap *= 2; pt = realloc(pt, sizeof(int64_t) * pcap); pa = realloc(pa, sizeof(int) * pcap); }
            pt[pn] = t - (int64_t)src * SECTION_MS * 1000;
            pa[pn] = a;
            pn++;
        }
    }
    Events ev = {0};
    for (size_t i = 0; i < orig.n; i++) {
        int64_t t = (int64_t)(orig.k[i] >> 12);
        int a = (int)(orig.k[i] & 4095);
        if (a < NP && pasted[t / 1000 / SECTION_MS]) continue;      /* replaced by the pattern */
        push(&ev, t, a);
    }
    free(orig.k); orig.k = NULL;   /* the original trains are no longer needed */
    long long count_pattern = 0;
    for (int i = 0; i < npaste; i++) {
        int64_t start = (int64_t)sel[i] * SECTION_MS * 1000;
        for (size_t j = 0; j < pn; j++) {
            int64_t t = start + pt[j] + (int64_t)llround(gauss() * JITTER_MS * 1000.0);
            if (t >= (int64_t)steps * 1000) t = (int64_t)steps * 1000 - 1;
            push(&ev, t, pa[j]);
            count_pattern++;
        }
    }
    /* 3. spontaneous activity, 10 Hz, to every afferent all the time, on the same 1 ms grid */
    long long count_spont = 0;
    for (int a = 0; a < N; a++)
        for (int t = 0; t < steps; t++)
            if (unif() < SPONT_HZ * DT_MS * 1e-3) { push(&ev, (int64_t)t * 1000, a); count_spont++; }
    radix(ev.k, ev.n);
    for (size_t i = 1; i < ev.n; i++) if (ev.k[i] < ev.k[i - 1]) die("events not sorted");

    /* 4. the neuron and STDP (rules 2 and 3), event by event over REP pastes of the train */
    double K = 1.0;
    {   /* K so that the EPSP kernel's maximum is 1 */
        double tp = log(TAU_M / TAU_S) * TAU_M * TAU_S / (TAU_M - TAU_S);
        K = 1.0 / (exp(-tp / TAU_M) - exp(-tp / TAU_S));
    }
    double *w = malloc(sizeof(double) * N);
    double *last_pre = malloc(sizeof(double) * N);
    char *since_post = calloc(N, 1);              /* a spike already arrived since the last post-synaptic spike */
    for (int a = 0; a < N; a++) { w[a] = W0; last_pre[a] = -1e18; }
    /* the EPSPs alive: a ring of (time, weight) in arrival order */
    size_t qcap = 1 << 22, qh = 0, qt = 0;
    double *qtm = malloc(sizeof(double) * qcap), *qw = malloc(sizeof(double) * qcap);
    double A = 0, B = 0, tA = 0;                  /* sums of w e^{-(t-tj)/tau_m}, w e^{-(t-tj)/tau_s} at time tA */
    double t_post = -1e18;
    size_t posts = 0, pcap2 = 1 << 16;
    double *post = malloc(sizeof(double) * pcap2);
    FILE *df = NULL;
    if (strcmp(dump, "-")) { df = fopen(dump, "w"); if (!df) die("cannot write the dump"); }
    double total_ms = (double)BASE * 1000.0 * REP;
    for (int rep = 0; rep < REP; rep++) {
        double off = (double)rep * BASE * 1000.0;
        for (size_t i = 0; i < ev.n; i++) {
            double t = off + (double)(ev.k[i] >> 12) / 1000.0;            /* ms */
            int a = (int)(ev.k[i] & 4095);
            /* bring the sums to t, dropping EPSPs older than the cut */
            double dA = exp(-(t - tA) / TAU_M), dB = exp(-(t - tA) / TAU_S);
            A *= dA; B *= dB; tA = t;
            while (qh != qt && t - qtm[qh % qcap] > CUT) {
                double age = t - qtm[qh % qcap];
                A -= qw[qh % qcap] * exp(-age / TAU_M);
                B -= qw[qh % qcap] * exp(-age / TAU_S);
                qh++;
            }
            /* the membrane potential just before this input */
            double eta = 0;
            double since = t - t_post;
            if (since >= 0 && since < CUT)
                eta = THRESHOLD * (K1 * exp(-since / TAU_M) - K2 * (exp(-since / TAU_M) - exp(-since / TAU_S)));
            double V = K * (A - B) + eta;
            if (V >= THRESHOLD && since >= REFRACTORY) {
                /* a post-synaptic spike at t: LTP of each afferent's last spike before it, if no post-synaptic
                   spike came between them (nearest spikes), then flush */
                if (stdp)
                    for (int j = 0; j < N; j++) {
                        double d = t - last_pre[j];
                        if (last_pre[j] > t_post && d >= 0 && d <= 7.0 * TAU_PLUS) {
                            w[j] += A_PLUS * exp(-d / TAU_PLUS);
                            if (w[j] > 1) w[j] = 1;
                        }
                    }
                memset(since_post, 0, N);
                A = B = 0; qh = qt = 0;
                t_post = t;
                if (posts == pcap2) { pcap2 *= 2; post = realloc(post, sizeof(double) * pcap2); }
                post[posts++] = t;
                if (df) fprintf(df, "post %.6f\n", t);
            }
            /* the input: LTD if it is its afferent's first spike since the last post-synaptic spike */
            if (stdp && !since_post[a]) {
                double d = t - t_post;
                if (d >= 0 && d <= 7.0 * TAU_MINUS) {
                    w[a] -= A_MINUS * exp(-d / TAU_MINUS);
                    if (w[a] < 0) w[a] = 0;
                }
            }
            since_post[a] = 1;
            last_pre[a] = t;
            A += w[a]; B += w[a];
            if (qt - qh == qcap) die("too many EPSPs alive");
            qtm[qt % qcap] = t; qw[qt % qcap] = w[a]; qt++;
            if (df && rep == 0 && i < 200000) fprintf(df, "in %.6f %d %.9f\n", t, a, w[a]);
        }
    }
    if (df) fclose(df);

    /* 5. the record: the pattern's presentations, and the post-synaptic spikes against them */
    FILE *f = fopen(out, "w");
    if (!f) die("cannot write the record");
    fprintf(f, "afferent_rate_original %.6f\n", (double)count_orig / N / BASE);
    fprintf(f, "afferent_rate_forced %.6f\n", (double)count_forced / N / BASE);
    fprintf(f, "afferent_rate_total %.6f\n", (double)ev.n / N / BASE);
    fprintf(f, "spontaneous_rate %.6f\n", (double)count_spont / N / BASE);
    fprintf(f, "pattern_spikes %zu\n", pn);
    fprintf(f, "pasted %d\n", npaste);
    int consecutive = 0;
    for (int i = 1; i < npaste; i++) consecutive += sel[i] == sel[i - 1] + 1;
    fprintf(f, "consecutive %d\n", consecutive);
    fprintf(f, "source_section %d\n", src);
    fprintf(f, "posts %zu\n", posts);
    fprintf(f, "total_ms %.3f\n", total_ms);
    fprintf(f, "sections");
    for (int i = 0; i < npaste; i++) fprintf(f, " %d", sel[i]);
    fprintf(f, "\npost");
    for (size_t i = 0; i < posts; i++) fprintf(f, " %.4f", post[i]);
    fprintf(f, "\nweights");
    for (int a = 0; a < N; a++) fprintf(f, " %.6f", w[a]);
    fprintf(f, "\n");
    fclose(f);
    return 0;
}
