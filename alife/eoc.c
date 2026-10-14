/* Mitchell, Hraber & Crutchfield (1993), "Revisiting the edge of chaos": the GA that evolves r = 3 cellular automata
 * for the density task rho_c = 1/2, as the paper's Section 7.1 specifies it. Driven by alife/eoc.py, which fixes every
 * rule and reads the results; this file holds only the simulation.
 *
 * Usage:
 *   eoc ga <s0> <s1> <s2> <s3> <generations> <select> <out>   one run; select 0 is the paper's no-selection control
 *   eoc fit <s0> <s1> <s2> <s3> <rulehex> <sets> <out>         a rule's proportional fitness on <sets> fresh IC sets
 *   eoc trace <rulehex> <icbits> <steps>                       the configuration after <steps> steps (no early stop)
 *
 * A rule is 128 output bits, bit k the state the neighbourhood k maps to, k read as a 7-bit number with the leftmost
 * cell (x - 3) the most significant bit (the paper: bit 0 for 0000000, bit 1 for 0000001, ...). Its hex form is 32
 * digits, most significant first (bit 127 first). A configuration is 149 cells on a ring.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define L 149
#define POP 100
#define ELITE 50
#define NIC 300
#define MEAN_M 320.0
#define MEAN_MUT 3.8

/* ------------------------------------------------------------------ xoshiro256** */
static uint64_t S[4];
static uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t next64(void) {
    uint64_t r = rotl(S[1] * 5, 7) * 9, t = S[1] << 17;
    S[2] ^= S[0]; S[3] ^= S[1]; S[1] ^= S[2]; S[0] ^= S[3]; S[2] ^= t; S[3] = rotl(S[3], 45);
    return r;
}
static uint64_t below(uint64_t n) {            /* uniform on 0..n-1, by rejection */
    uint64_t lim = UINT64_MAX - (UINT64_MAX % n);
    for (;;) { uint64_t x = next64(); if (x < lim) return x % n; }
}
static double unif(void) { return (next64() >> 11) * (1.0 / 9007199254740992.0); }
static int poisson(double mean) {              /* Knuth's method */
    double lim = exp(-mean), p = 1.0; int k = 0;
    do { k++; p *= unif(); } while (p > lim);
    return k - 1;
}

/* ------------------------------------------------------------------ rules and configurations */
typedef struct { uint64_t b[2]; } Rule;        /* bit k of the rule: b[k >> 6] >> (k & 63) */
typedef struct { uint64_t w[3]; } Row;         /* cells 0..148 */

static int rule_bit(const Rule *r, int k) { return (int)((r->b[k >> 6] >> (k & 63)) & 1); }
static void rule_flip(Rule *r, int k) { r->b[k >> 6] ^= (uint64_t)1 << (k & 63); }
static int rule_ones(const Rule *r) { return __builtin_popcountll(r->b[0]) + __builtin_popcountll(r->b[1]); }
static int cell(const Row *x, int i) { return (int)((x->w[i >> 6] >> (i & 63)) & 1); }
static void set_cell(Row *x, int i) { x->w[i >> 6] |= (uint64_t)1 << (i & 63); }
static int ones(const Row *x) {
    return __builtin_popcountll(x->w[0]) + __builtin_popcountll(x->w[1]) + __builtin_popcountll(x->w[2]);
}

static void rule_hex(const Rule *r, char *out) {
    sprintf(out, "%016llx%016llx", (unsigned long long)r->b[1], (unsigned long long)r->b[0]);
}
static int rule_from_hex(const char *s, Rule *r) {
    char hi[17], lo[17];
    if (strlen(s) != 32) return 0;
    memcpy(hi, s, 16); hi[16] = 0; memcpy(lo, s + 16, 16); lo[16] = 0;
    r->b[1] = strtoull(hi, NULL, 16); r->b[0] = strtoull(lo, NULL, 16);
    return 1;
}

/* The 2^14 table: a window of 14 cells (c - 3 .. c + 10, bit i the cell c - 3 + i) to the 8 next states of
 * cells c .. c + 7. */
static uint8_t T[1 << 14];
static void build_table(const Rule *r) {
    for (int idx = 0; idx < (1 << 14); idx++) {
        uint8_t out = 0;
        for (int b = 0; b < 8; b++) {
            int nb = 0;
            for (int i = 0; i < 7; i++) nb = (nb << 1) | ((idx >> (b + i)) & 1);   /* cell c+b-3 first: MSB */
            out |= (uint8_t)(rule_bit(r, nb) << b);
        }
        T[idx] = out;
    }
}

static const uint64_t TOP = ((uint64_t)1 << 21) - 1;   /* cells 128..148 in w[2] */

static void step(const Row *x, Row *y) {
    uint64_t e[3];                              /* bit k: cell (k - 3) mod 149, k = 0..191 */
    e[0] = (x->w[0] << 3) | ((x->w[2] >> 18) & 7);
    e[1] = (x->w[1] << 3) | (x->w[0] >> 61);
    e[2] = (x->w[2] << 3) | (x->w[1] >> 61) | ((x->w[0] & (((uint64_t)1 << 40) - 1)) << 24);
    y->w[0] = y->w[1] = y->w[2] = 0;
    for (int j = 0; j < 19; j++) {
        int c = 8 * j, wd = c >> 6, off = c & 63;
        uint64_t v = e[wd] >> off;
        if (off > 50 && wd < 2) v |= e[wd + 1] << (64 - off);
        y->w[wd] |= (uint64_t)T[v & 0x3FFF] << off;
    }
    y->w[2] &= TOP;
}

/* A configuration with exactly k ones, uniformly among them. */
static void random_ic(Row *x, int k) {
    int perm[L];
    for (int i = 0; i < L; i++) perm[i] = i;
    for (int i = L - 1; i > 0; i--) { int j = (int)below((uint64_t)i + 1), t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
    x->w[0] = x->w[1] = x->w[2] = 0;
    for (int i = 0; i < k; i++) set_cell(x, perm[i]);
}

/* 300 configurations: 150 with k uniform on 0..74 (density below 1/2), 150 with k uniform on 75..149. */
static Row ICS[NIC];
static int ICK[NIC];
static void new_ics(void) {
    for (int i = 0; i < NIC; i++) {
        int k = i < NIC / 2 ? (int)below(75) : 75 + (int)below(75);
        ICK[i] = k; random_ic(&ICS[i], k);
    }
}

/* Proportional fitness: the mean, over the 300 configurations, of the fraction of cells in the correct state (all 1 if
 * the density is above 1/2, all 0 if below) after M steps; a run stops early at a fixed point, which changes nothing. */
static double fitness(const Rule *r, int M) {
    build_table(r);
    double total = 0.0;
    for (int i = 0; i < NIC; i++) {
        Row a = ICS[i], b;
        for (int t = 0; t < M; t++) {
            step(&a, &b);
            if (b.w[0] == a.w[0] && b.w[1] == a.w[1] && b.w[2] == a.w[2]) break;
            a = b;
        }
        int n1 = ones(&a);
        total += (ICK[i] > L / 2 ? n1 : L - n1) / (double)L;
    }
    return total / NIC;
}

/* An initial rule: its number of ones uniform on 0..128, then uniformly placed. */
static void random_rule(Rule *r) {
    int n = (int)below(129), perm[128];
    for (int i = 0; i < 128; i++) perm[i] = i;
    for (int i = 127; i > 0; i--) { int j = (int)below((uint64_t)i + 1), t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
    r->b[0] = r->b[1] = 0;
    for (int i = 0; i < n; i++) rule_flip(r, perm[i]);
}

static void crossover(const Rule *p, const Rule *q, Rule *a, Rule *b) {
    int c = 1 + (int)below(127);               /* bits 0..c-1 from one parent, c..127 from the other */
    for (int k = 0; k < 128; k++) {
        int from_p = k < c;
        int bp = rule_bit(p, k), bq = rule_bit(q, k);
        int va = from_p ? bp : bq, vb = from_p ? bq : bp;
        if (va != rule_bit(a, k)) rule_flip(a, k);
        if (vb != rule_bit(b, k)) rule_flip(b, k);
    }
}
static void mutate(Rule *r) {
    int n = poisson(MEAN_MUT);
    for (int i = 0; i < n; i++) rule_flip(r, (int)below(128));
}

typedef struct { double f; int i; } Ranked;
static int by_fitness(const void *x, const void *y) {
    const Ranked *a = x, *b = y;
    if (a->f != b->f) return a->f < b->f ? 1 : -1;  /* descending */
    return a->i - b->i;                             /* ties: earlier index first */
}

static int seed_from(char **argv) {
    for (int i = 0; i < 4; i++) S[i] = strtoull(argv[i], NULL, 16);
    return (S[0] | S[1] | S[2] | S[3]) != 0;
}

/* One run. Each generation g = 0..G: a fresh set of 300 configurations, every rule's fitness (with selection), the
 * record; then, for g < G, the next population: the top half kept (with selection; a random half without), and 25
 * pairs of parents drawn with replacement from the whole population giving two offspring each by one-point crossover,
 * each mutated. */
static int run_ga(int G, int select, const char *out) {
    Rule pop[POP], next[POP];
    double fit[POP];
    FILE *fh = fopen(out, "w");
    if (!fh) return 2;
    for (int i = 0; i < POP; i++) random_rule(&pop[i]);
    for (int g = 0; g <= G; g++) {
        Ranked rk[POP];
        if (select) {
            new_ics();
            for (int i = 0; i < POP; i++) fit[i] = fitness(&pop[i], poisson(MEAN_M));
        } else {
            for (int i = 0; i < POP; i++) fit[i] = unif();          /* a random order: no selection */
        }
        for (int i = 0; i < POP; i++) { rk[i].f = fit[i]; rk[i].i = i; }
        qsort(rk, POP, sizeof rk[0], by_fitness);
        fprintf(fh, "gen %d", g);
        for (int i = 0; i < POP; i++) fprintf(fh, " %d", rule_ones(&pop[i]));
        fprintf(fh, "\n");
        if (g == G) {
            for (int i = 0; i < POP; i++) {
                char hx[33]; rule_hex(&pop[rk[i].i], hx);
                fprintf(fh, "final %d %s %d %.6f %d\n", i, hx, rule_ones(&pop[rk[i].i]), select ? rk[i].f : -1.0,
                        i < ELITE);
            }
            break;
        }
        for (int i = 0; i < ELITE; i++) next[i] = pop[rk[i].i];
        for (int j = 0; j < (POP - ELITE) / 2; j++) {
            const Rule *p = &pop[below(POP)], *q = &pop[below(POP)];
            Rule a = {{0, 0}}, b = {{0, 0}};
            crossover(p, q, &a, &b);
            mutate(&a); mutate(&b);
            next[ELITE + 2 * j] = a; next[ELITE + 2 * j + 1] = b;
        }
        memcpy(pop, next, sizeof pop);
    }
    fclose(fh);
    return 0;
}

static int run_fit(const char *hex, int sets, const char *out) {
    Rule r;
    FILE *fh;
    if (!rule_from_hex(hex, &r)) return 2;
    fh = fopen(out, "w");
    if (!fh) return 2;
    for (int s = 0; s < sets; s++) { new_ics(); fprintf(fh, "%.9f\n", fitness(&r, poisson(MEAN_M))); }
    fclose(fh);
    return 0;
}

static int run_trace(const char *hex, const char *bits, int steps) {
    Rule r; Row a = {{0, 0, 0}}, b;
    if (!rule_from_hex(hex, &r) || strlen(bits) != L) return 2;
    for (int i = 0; i < L; i++) if (bits[i] == '1') set_cell(&a, i);
    build_table(&r);
    for (int t = 0; t < steps; t++) { step(&a, &b); a = b; }
    for (int i = 0; i < L; i++) putchar('0' + cell(&a, i));
    putchar('\n');
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 9 && !strcmp(argv[1], "ga")) {
        if (!seed_from(argv + 2)) return 2;
        return run_ga(atoi(argv[6]), atoi(argv[7]), argv[8]);
    }
    if (argc >= 9 && !strcmp(argv[1], "fit")) {
        if (!seed_from(argv + 2)) return 2;
        return run_fit(argv[6], atoi(argv[7]), argv[8]);
    }
    if (argc >= 5 && !strcmp(argv[1], "trace")) return run_trace(argv[2], argv[3], atoi(argv[4]));
    fprintf(stderr, "usage: eoc ga|fit|trace ...\n");
    return 2;
}
