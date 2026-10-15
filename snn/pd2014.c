/* pd2014.c: Potjans & Diesmann's (2014) full-scale cortical microcircuit, for snn/pd2014.py.
 *
 * Imago's laboratory. Current-based leaky integrate-and-fire neurons with exponential synaptic currents, updated on
 * a 0.1 ms grid as NEST 2.4's iaf_psc_exp updates them (exact integration: the membrane from the current of the
 * step before, then the current's decay, then the step's arrivals, then the threshold), connected by the
 * fixed-total-number rule (every synapse's presynaptic and postsynaptic neuron drawn independently and uniformly
 * from its populations, multapses and autapses allowed), with Gaussian weights and delays redrawn until they keep
 * their sign or reach the lowest delay, and independent Poisson background arrivals to every neuron.
 *
 * Every number the model needs (populations, synapse counts, weights, delays, propagators, the background's Poisson
 * tables and the generators' seeds) comes from a configuration file the Python module writes; nothing here is
 * tuned. Two threads: each updates one half of the neurons and delivers every spike to the targets in its half, so
 * results do not depend on how the threads are scheduled.
 *
 * Usage:
 *   pd2014 run CONFIG          build, simulate, write the files the configuration names, print key=value lines
 *   pd2014 psp P11 P21 P22 W   one neuron at rest, one arrival of W: print the peak and its step
 *
 * The generator is xoshiro256** (the Python module's, word for word); Gaussians by Box-Muller from two uniforms.
 */
#define _GNU_SOURCE
#include <math.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define NP 8
#define PTAB 64

typedef struct { uint64_t s[4]; } rng_t;

static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static inline uint64_t nx(rng_t *r) {
    uint64_t *s = r->s;
    uint64_t res = rotl(s[1] * 5, 7) * 9;
    uint64_t t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return res;
}
static inline double unif(rng_t *r) { return (double)(nx(r) >> 11) * 0x1.0p-53; }
static inline uint32_t below(rng_t *r, uint32_t m) { return (uint32_t)(unif(r) * (double)m); }
static inline double gauss(rng_t *r) {
    double u1 = 1.0 - unif(r), u2 = unif(r);
    return sqrt(-2.0 * log(u1)) * cos(2.0 * M_PI * u2);
}

/* ------------------------------------------------------------------ configuration */

static uint32_t Npop[NP], base[NP + 1], Ntot, hb[3];
static uint64_t K[NP][NP];                  /* [target][source] */
static double wmean[NP][NP], wsd[NP][NP];   /* pA, [target][source] */
static double dmean[NP], dsd[NP], dlow, steps_per_ms;
static double kext_w;                       /* background weight, pA */
static double ptab[NP][PTAB];               /* background Poisson CDF per population, per step */
static uint8_t guide[NP][4096];             /* guide table: the least k with ptab[k] > b / 4096 */
static double P11, P21, P22, theta, vreset; /* V relative to E_L */
static int refc;
static double v0mean, v0sd;                 /* relative to E_L */
static long warm, recn;                     /* steps */
static uint32_t nrec;
static rng_t conn_w[NP][NP], del_w[NP][NP], wgt_w, v0_w, bg_w[2];
static char spikes_path[2][4096], counts_path[4096], v_path[4096];
static int dump_state, forced;
static double fprob[NP];                    /* timing only: spikes forced at these probabilities a step */

static void die(const char *m) { fprintf(stderr, "pd2014: %s\n", m); exit(2); }

static void words(char **tok, rng_t *r) {
    for (int i = 0; i < 4; i++) r->s[i] = strtoull(tok[i], NULL, 16);
    if (!(r->s[0] | r->s[1] | r->s[2] | r->s[3])) r->s[0] = 1;
}

static void read_config(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) die("cannot open the configuration");
    char line[1 << 16];
    int seen = 0;
    while (fgets(line, sizeof line, f)) {
        char *tok[80]; int n = 0;
        for (char *p = strtok(line, " \t\r\n"); p && n < 80; p = strtok(NULL, " \t\r\n")) tok[n++] = p;
        if (n == 0) continue;
        char *k = tok[0];
        if (!strcmp(k, "N")) { for (int i = 0; i < NP; i++) Npop[i] = (uint32_t)strtoul(tok[1 + i], NULL, 10); seen |= 1; }
        else if (!strcmp(k, "K")) { int t = atoi(tok[1]); for (int s = 0; s < NP; s++) K[t][s] = strtoull(tok[2 + s], NULL, 10); }
        else if (!strcmp(k, "wmean")) { int t = atoi(tok[1]); for (int s = 0; s < NP; s++) wmean[t][s] = strtod(tok[2 + s], NULL); }
        else if (!strcmp(k, "wsd")) { int t = atoi(tok[1]); for (int s = 0; s < NP; s++) wsd[t][s] = strtod(tok[2 + s], NULL); }
        else if (!strcmp(k, "dmean")) { for (int s = 0; s < NP; s++) dmean[s] = strtod(tok[1 + s], NULL); }
        else if (!strcmp(k, "dsd")) { for (int s = 0; s < NP; s++) dsd[s] = strtod(tok[1 + s], NULL); }
        else if (!strcmp(k, "dlow")) dlow = strtod(tok[1], NULL);
        else if (!strcmp(k, "steps_per_ms")) steps_per_ms = strtod(tok[1], NULL);
        else if (!strcmp(k, "wext")) kext_w = strtod(tok[1], NULL);
        else if (!strcmp(k, "ptab")) { int p = atoi(tok[1]); if (n != 2 + PTAB) die("ptab"); for (int j = 0; j < PTAB; j++) ptab[p][j] = strtod(tok[2 + j], NULL); }
        else if (!strcmp(k, "prop")) { P11 = strtod(tok[1], NULL); P21 = strtod(tok[2], NULL); P22 = strtod(tok[3], NULL); }
        else if (!strcmp(k, "theta")) theta = strtod(tok[1], NULL);
        else if (!strcmp(k, "vreset")) vreset = strtod(tok[1], NULL);
        else if (!strcmp(k, "refc")) refc = atoi(tok[1]);
        else if (!strcmp(k, "v0")) { v0mean = strtod(tok[1], NULL); v0sd = strtod(tok[2], NULL); }
        else if (!strcmp(k, "steps")) { warm = atol(tok[1]); recn = atol(tok[2]); }
        else if (!strcmp(k, "nrec")) nrec = (uint32_t)strtoul(tok[1], NULL, 10);
        else if (!strcmp(k, "conn")) { int t = atoi(tok[1]), s = atoi(tok[2]); words(tok + 3, &conn_w[t][s]); }
        else if (!strcmp(k, "delay")) { int t = atoi(tok[1]), s = atoi(tok[2]); words(tok + 3, &del_w[t][s]); }
        else if (!strcmp(k, "weight")) words(tok + 1, &wgt_w);
        else if (!strcmp(k, "vinit")) words(tok + 1, &v0_w);
        else if (!strcmp(k, "bg")) { int t = atoi(tok[1]); words(tok + 2, &bg_w[t]); }
        else if (!strcmp(k, "spikes")) { snprintf(spikes_path[0], 4096, "%s.0", tok[1]); snprintf(spikes_path[1], 4096, "%s.1", tok[1]); }
        else if (!strcmp(k, "counts")) snprintf(counts_path, 4096, "%s", tok[1]);
        else if (!strcmp(k, "state")) { snprintf(v_path, 4096, "%s", tok[1]); dump_state = 1; }
        else if (!strcmp(k, "force")) { for (int s = 0; s < NP; s++) fprob[s] = strtod(tok[1 + s], NULL); forced = 1; }
        else { fprintf(stderr, "pd2014: unknown key %s\n", k); exit(2); }
    }
    fclose(f);
    if (!(seen & 1)) die("no populations");
    base[0] = 0;
    for (int i = 0; i < NP; i++) base[i + 1] = base[i] + Npop[i];
    Ntot = base[NP];
    hb[0] = 0; hb[1] = Ntot / 2; hb[2] = Ntot;
    if (Ntot - hb[1] > 65535) die("a half holds more than 65535 neurons");
    for (int p = 0; p < NP; p++) for (int b = 0; b < 4096; b++) {
        int k = 0; double lo = b * 0x1.0p-12;
        while (k < PTAB - 1 && ptab[p][k] <= lo) k++;
        guide[p][b] = (uint8_t)k;
    }
}

/* ------------------------------------------------------------------ the network */

static uint8_t *popof;          /* population of each neuron */
static uint64_t *seg;           /* 2 Ntot + 1: start of segment (pre j, half h) at seg[2 j + h] */
static uint64_t *grp;           /* 2 Ntot + 1: start of its delay groups */
static uint8_t *gdel;           /* delay of each group, steps */
static uint32_t *gcnt;          /* synapses in each group */
static uint16_t *tgt;           /* target, relative to its half's first neuron */
static float *wgt;              /* pA */
static uint64_t S;              /* synapses */
static int maxdel, D;
static uint64_t delay_redraws, weight_redraws;
static double dsum[2], dsq[2]; static uint64_t dn[2];      /* delays by source type (e, i), ms */
static double wsum[3], wsq[3]; static uint64_t wn[3];      /* weights: e, i, L4e -> L2/3e */
static uint64_t indeg_n[NP][NP]; static double indeg_m[NP][NP], indeg_v[NP][NP];

static void radix3(uint32_t *a, uint32_t *tmp, uint64_t n) {
    for (int pass = 0; pass < 3; pass++) {
        int sh = 8 * pass; uint64_t c[257];
        memset(c, 0, sizeof c);
        for (uint64_t i = 0; i < n; i++) c[((a[i] >> sh) & 255) + 1]++;
        for (int b = 0; b < 256; b++) c[b + 1] += c[b];
        for (uint64_t i = 0; i < n; i++) tmp[c[(a[i] >> sh) & 255]++] = a[i];
        memcpy(a, tmp, n * sizeof *a);
    }
}

static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + 1e-9 * t.tv_nsec; }

static void build(void) {
    popof = malloc(Ntot);
    for (int p = 0; p < NP; p++) for (uint32_t i = base[p]; i < base[p + 1]; i++) popof[i] = (uint8_t)p;
    uint32_t *cnt = calloc(2 * (size_t)Ntot, sizeof *cnt);
    uint32_t *indeg = calloc((size_t)Ntot * NP, sizeof *indeg);
    if (!cnt || !indeg) die("memory (counts)");
    /* pass 1: out-degrees by half, and in-degrees by source population */
    for (int t = 0; t < NP; t++) for (int s = 0; s < NP; s++) {
        rng_t r = conn_w[t][s];
        for (uint64_t k = 0; k < K[t][s]; k++) {
            uint32_t pre = base[s] + below(&r, Npop[s]);
            uint32_t post = base[t] + below(&r, Npop[t]);
            cnt[2 * (size_t)pre + (post >= hb[1])]++;
            indeg[(size_t)post * NP + s]++;
        }
    }
    for (int t = 0; t < NP; t++) for (int s = 0; s < NP; s++) {
        double m = 0, q = 0; uint64_t n = Npop[t];
        for (uint32_t i = base[t]; i < base[t + 1]; i++) { double x = indeg[(size_t)i * NP + s]; m += x; q += x * x; }
        indeg_n[t][s] = n; indeg_m[t][s] = m / n; indeg_v[t][s] = q / n - (m / n) * (m / n);
    }
    free(indeg);
    seg = malloc((2 * (size_t)Ntot + 1) * sizeof *seg);
    S = 0;
    for (size_t i = 0; i < 2 * (size_t)Ntot; i++) { seg[i] = S; S += cnt[i]; }
    seg[2 * (size_t)Ntot] = S;
    uint32_t *keys = malloc(S * sizeof *keys);
    uint64_t *fill = malloc(2 * (size_t)Ntot * sizeof *fill);
    if (!keys || !fill) die("memory (keys)");
    memcpy(fill, seg, 2 * (size_t)Ntot * sizeof *fill);
    /* pass 2: the same pairs again, each with its delay */
    maxdel = 0; delay_redraws = 0;
    for (int t = 0; t < NP; t++) for (int s = 0; s < NP; s++) {
        rng_t r = conn_w[t][s], rd = del_w[t][s];
        int ty = s & 1;
        for (uint64_t k = 0; k < K[t][s]; k++) {
            uint32_t pre = base[s] + below(&r, Npop[s]);
            uint32_t post = base[t] + below(&r, Npop[t]);
            double x = dmean[s] + dsd[s] * gauss(&rd);
            while (x < dlow) { delay_redraws++; x = dmean[s] + dsd[s] * gauss(&rd); }
            uint32_t st = (uint32_t)floor(x * steps_per_ms + 0.5);
            if (st < 1) st = 1;
            if (st > 255) die("a delay longer than 255 steps");
            if ((int)st > maxdel) maxdel = (int)st;
            dsum[ty] += st / steps_per_ms; dsq[ty] += (st / steps_per_ms) * (st / steps_per_ms); dn[ty]++;
            int h = post >= hb[1];
            keys[fill[2 * (size_t)pre + h]++] = (st << 16) | (post - hb[h]);
        }
    }
    free(fill); free(cnt);
    /* sort each segment by (delay, target); count the delay groups */
    uint64_t maxseg = 0, ngrp = 0;
    for (size_t i = 0; i < 2 * (size_t)Ntot; i++) if (seg[i + 1] - seg[i] > maxseg) maxseg = seg[i + 1] - seg[i];
    uint32_t *tmp = malloc((maxseg + 1) * sizeof *tmp);
    for (size_t i = 0; i < 2 * (size_t)Ntot; i++) {
        uint64_t a = seg[i], b = seg[i + 1];
        radix3(keys + a, tmp, b - a);
        for (uint64_t p = a; p < b; p++) if (p == a || (keys[p] >> 16) != (keys[p - 1] >> 16)) ngrp++;
    }
    free(tmp);
    grp = malloc((2 * (size_t)Ntot + 1) * sizeof *grp);
    gdel = malloc(ngrp + 1); gcnt = malloc((ngrp + 1) * sizeof *gcnt);
    tgt = malloc(S * sizeof *tgt);
    if (!grp || !gdel || !gcnt || !tgt) die("memory (groups)");
    uint64_t g = 0;
    for (size_t i = 0; i < 2 * (size_t)Ntot; i++) {
        grp[i] = g;
        for (uint64_t p = seg[i]; p < seg[i + 1]; p++) {
            if (p == seg[i] || (keys[p] >> 16) != (keys[p - 1] >> 16)) { gdel[g] = (uint8_t)(keys[p] >> 16); gcnt[g] = 0; g++; }
            gcnt[g - 1]++;
            tgt[p] = (uint16_t)(keys[p] & 0xFFFF);
        }
    }
    grp[2 * (size_t)Ntot] = g;
    free(keys);
    /* weights, in storage order */
    wgt = malloc(S * sizeof *wgt);
    if (!wgt) die("memory (weights)");
    rng_t rw = wgt_w; weight_redraws = 0;
    for (uint32_t j = 0; j < Ntot; j++) for (int h = 0; h < 2; h++) {
        size_t i = 2 * (size_t)j + h; int sp = popof[j];
        for (uint64_t p = seg[i]; p < seg[i + 1]; p++) {
            int tp = popof[hb[h] + tgt[p]];
            double mu = wmean[tp][sp], sd = wsd[tp][sp];
            double x = mu + sd * gauss(&rw);
            while ((mu > 0 && x < 0) || (mu < 0 && x > 0)) { weight_redraws++; x = mu + sd * gauss(&rw); }
            wgt[p] = (float)x;
            int c = (sp == 2 && tp == 0) ? 2 : (sp & 1);
            double xf = (double)wgt[p];
            wsum[c] += xf; wsq[c] += xf * xf; wn[c]++;
        }
    }
    D = 1; while (D <= maxdel) D <<= 1;
}

/* ------------------------------------------------------------------ the simulation */

static double *V, *I, *ring[2];
static int *ref;
static uint32_t *spk[2], ns[2];
static uint32_t *cnt_all;
static uint64_t bg_arr[2][NP], deliveries[2], all_spikes;
static pthread_barrier_t bar;
static FILE *sf[2];

static void *worker(void *arg) {
    int th = (int)(intptr_t)arg;
    uint32_t lo = hb[th], hi = hb[th + 1], nh = hi - lo;
    rng_t rb = bg_w[th];
    double *rg = ring[th];
    uint32_t *buf = malloc(4 * (size_t)nh * sizeof *buf); size_t nb = 0;
    uint64_t bgc[NP] = {0};
    long total = warm + recn;
    for (long n = 0; n < total; n++) {
        int slot = (int)(n & (D - 1));
        double *rr = rg + (size_t)slot * nh;
        int rec = n >= warm;
        ns[th] = 0;
        for (uint32_t i = lo; i < hi; i++) {
            uint32_t li = i - lo;
            double in = rr[li]; rr[li] = 0.0;
            if (ref[i] == 0) V[i] = V[i] * P22 + I[i] * P21;
            else ref[i]--;
            int p = popof[i];
            uint64_t x = nx(&rb);
            double u = (double)(x >> 11) * 0x1.0p-53; int k = guide[p][x >> 52];
            while (k < PTAB - 1 && u >= ptab[p][k]) k++;
            I[i] = I[i] * P11 + in + k * kext_w;
            if (rec) bgc[p] += (uint64_t)k;
            if (forced ? unif(&rb) < fprob[p] : V[i] >= theta) {
                ref[i] = refc; V[i] = vreset;
                spk[th][ns[th]++] = i;
                if (rec) {
                    cnt_all[i]++;
                    if (i - base[p] < nrec) { buf[nb++] = i; buf[nb++] = (uint32_t)(n - warm); }
                }
            }
        }
        if (nb >= 2 * (size_t)nh) { fwrite(buf, sizeof *buf, nb, sf[th]); nb = 0; }
        pthread_barrier_wait(&bar);
        uint64_t dl = 0;
        for (int o = 0; o < 2; o++) for (uint32_t q = 0; q < ns[o]; q++) {
            uint32_t j = spk[o][q]; size_t s = 2 * (size_t)j + th;
            uint64_t p = seg[s];
            for (uint64_t g = grp[s]; g < grp[s + 1]; g++) {
                double *r2 = rg + (size_t)((n + gdel[g]) & (D - 1)) * nh;
                uint32_t c = gcnt[g];
                for (uint32_t m = 0; m < c; m++, p++) r2[tgt[p]] += (double)wgt[p];
                dl += c;
            }
        }
        deliveries[th] += dl;
        pthread_barrier_wait(&bar);
    }
    if (nb) fwrite(buf, sizeof *buf, nb, sf[th]);
    free(buf);
    for (int p = 0; p < NP; p++) bg_arr[th][p] = bgc[p];
    return NULL;
}

static int cmd_run(const char *cfg) {
    read_config(cfg);
    double t0 = now();
    build();
    double t1 = now();
    V = malloc(Ntot * sizeof *V); I = calloc(Ntot, sizeof *I); ref = calloc(Ntot, sizeof *ref);
    rng_t rv = v0_w;
    for (uint32_t i = 0; i < Ntot; i++) V[i] = v0mean + v0sd * gauss(&rv);
    for (int h = 0; h < 2; h++) {
        ring[h] = calloc((size_t)D * (hb[h + 1] - hb[h]), sizeof(double));
        spk[h] = malloc((hb[h + 1] - hb[h] + 1) * sizeof(uint32_t));
        sf[h] = fopen(spikes_path[h], "wb");
        if (!ring[h] || !spk[h] || !sf[h]) die("memory or files (simulation)");
    }
    cnt_all = calloc(Ntot, sizeof *cnt_all);
    pthread_barrier_init(&bar, NULL, 2);
    pthread_t a, b;
    pthread_create(&a, NULL, worker, (void *)(intptr_t)0);
    pthread_create(&b, NULL, worker, (void *)(intptr_t)1);
    pthread_join(a, NULL); pthread_join(b, NULL);
    double t2 = now();
    fclose(sf[0]); fclose(sf[1]);
    FILE *cf = fopen(counts_path, "wb");
    if (!cf) die("counts file");
    fwrite(cnt_all, sizeof *cnt_all, Ntot, cf); fclose(cf);
    if (dump_state) {
        FILE *vf = fopen(v_path, "wb");
        fwrite(V, sizeof *V, Ntot, vf); fwrite(I, sizeof *I, Ntot, vf); fwrite(ref, sizeof *ref, Ntot, vf);
        fclose(vf);
    }
    for (uint32_t i = 0; i < Ntot; i++) all_spikes += cnt_all[i];
    printf("neurons=%u\nsynapses=%llu\n", Ntot, (unsigned long long)S);
    uint64_t se = 0, si = 0;
    for (int t = 0; t < NP; t++) for (int s = 0; s < NP; s++) { if (s & 1) si += K[t][s]; else se += K[t][s]; }
    printf("synapses_e=%llu\nsynapses_i=%llu\n", (unsigned long long)se, (unsigned long long)si);
    printf("max_delay_steps=%d\nring=%d\ndelay_redraws=%llu\nweight_redraws=%llu\n", maxdel, D,
           (unsigned long long)delay_redraws, (unsigned long long)weight_redraws);
    for (int ty = 0; ty < 2; ty++) {
        double m = dsum[ty] / dn[ty];
        printf("delay_%c=%.17g,%.17g,%llu\n", ty ? 'i' : 'e', m, sqrt(dsq[ty] / dn[ty] - m * m), (unsigned long long)dn[ty]);
    }
    for (int c = 0; c < 3; c++) {
        double m = wn[c] ? wsum[c] / wn[c] : 0;
        printf("weight_%d=%.17g,%.17g,%llu\n", c, m, wn[c] ? sqrt(wsq[c] / wn[c] - m * m) : 0, (unsigned long long)wn[c]);
    }
    for (int t = 0; t < NP; t++) {
        printf("indeg_%d=", t);
        for (int s = 0; s < NP; s++) printf("%s%.17g:%.17g", s ? "," : "", indeg_m[t][s], indeg_v[t][s]);
        printf("\n");
    }
    printf("bg_arrivals=");
    for (int p = 0; p < NP; p++) printf("%s%llu", p ? "," : "", (unsigned long long)(bg_arr[0][p] + bg_arr[1][p]));
    printf("\nspikes=%llu\ndeliveries=%llu\nbuild_s=%.1f\nsim_s=%.1f\n", (unsigned long long)all_spikes,
           (unsigned long long)(deliveries[0] + deliveries[1]), t1 - t0, t2 - t1);
    return 0;
}

static int cmd_psp(char **a) {
    double p11 = strtod(a[0], NULL), p21 = strtod(a[1], NULL), p22 = strtod(a[2], NULL), w = strtod(a[3], NULL);
    double v = 0, i = 0, best = -1; int at = -1;
    for (int n = 0; n < 2000; n++) {
        v = v * p22 + i * p21;
        i = i * p11 + (n == 0 ? w : 0.0);
        if (v > best) { best = v; at = n; }
    }
    printf("peak=%.17g\nstep=%d\n", best, at);
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 3 && !strcmp(argv[1], "run")) return cmd_run(argv[2]);
    if (argc == 6 && !strcmp(argv[1], "psp")) return cmd_psp(argv + 2);
    fprintf(stderr, "usage: pd2014 run CONFIG | pd2014 psp P11 P21 P22 W\n");
    return 2;
}
