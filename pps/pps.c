/* The primordial particle system of Schmickl, Stefanec & Crailsheim (Sci. Rep. 6, 37969, 2016), as its Method and
   Figure 1 state it. Imago's laboratory; see pps/check.py for the rules and the test.

   usage:  pps run   <seed> <particles> <side> <steps> <every> <mirror 0|1>
           pps trace <seed> <particles> <side> <steps>

   run prints, at step 0 and every <every> steps after all particles have moved:
       t  over15  blue  yellow  brown  magenta_printed  magenta_first  blue_mf  yellow_mf
   counting, for every particle, the others within 5 (N5) and within 1.3 (N13):
       over15 = N5 > 15; blue = 15 < N5 <= 35; yellow = N5 > 35; brown = 13 <= N5 <= 15;
       magenta_printed = the printed rule's magenta, reached only when N5 < 13: N5 < 13 and N13 > 15;
       magenta_first = N13 > 15; blue_mf and yellow_mf = blue and yellow among the others.
   trace prints every particle's x, y and heading after <steps> steps, in C's %a (exact).
   mirror 1 turns by alpha - beta N sign(R - L): the rule misread, for a control. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

static uint64_t s[4];
static inline uint64_t rotl(const uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t next(void) {                                   /* xoshiro256** */
    const uint64_t result = rotl(s[1] * 5, 7) * 9;
    const uint64_t t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return result;
}
static uint64_t splitmix(uint64_t *x) {
    uint64_t z = (*x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
static double unif(void) { return (double)(next() >> 11) * (1.0 / 9007199254740992.0); }
static uint64_t below(uint64_t n) {
    uint64_t lim = UINT64_MAX - (UINT64_MAX % n);
    for (;;) { uint64_t x = next(); if (x < lim) return x % n; }
}

#define RADIUS 5.0
#define SPEED 0.67
static int n, G;
static double side, cellw;
static double *x, *y, *phi;
static int *head, *nxt, *prv, *cellof;

static int cell_of(double px, double py) {
    int cx = (int)(px / cellw), cy = (int)(py / cellw);
    if (cx >= G) cx = G - 1;
    if (cy >= G) cy = G - 1;
    return cy * G + cx;
}
static void insert(int i, int c) {
    prv[i] = -1; nxt[i] = head[c];
    if (head[c] >= 0) prv[head[c]] = i;
    head[c] = i; cellof[i] = c;
}
static void removep(int i) {
    int c = cellof[i];
    if (prv[i] >= 0) nxt[prv[i]] = nxt[i]; else head[c] = nxt[i];
    if (nxt[i] >= 0) prv[nxt[i]] = prv[i];
}
static inline double wrapd(double d) {
    if (d > side / 2) d -= side;
    else if (d < -side / 2) d += side;
    return d;
}
/* the others within RADIUS of particle i: on its left (cross < 0), on its right (cross > 0) */
static void sense(int i, int *L, int *R) {
    int cx = cellof[i] % G, cy = cellof[i] / G, l = 0, r = 0;
    double hx = cos(phi[i]), hy = sin(phi[i]), r2 = RADIUS * RADIUS;
    for (int dy = -1; dy <= 1; dy++)
        for (int dx = -1; dx <= 1; dx++) {
            int c = ((cy + dy + G) % G) * G + (cx + dx + G) % G;
            for (int j = head[c]; j >= 0; j = nxt[j]) {
                if (j == i) continue;
                double ddx = wrapd(x[j] - x[i]), ddy = wrapd(y[j] - y[i]);
                if (ddx * ddx + ddy * ddy > r2) continue;
                double cr = hx * ddy - hy * ddx;
                if (cr > 0) r++;
                else if (cr < 0) l++;
            }
        }
    *L = l; *R = r;
}
static int within(int i, double rad) {
    int cx = cellof[i] % G, cy = cellof[i] / G, k = 0;
    double r2 = rad * rad;
    for (int dy = -1; dy <= 1; dy++)
        for (int dx = -1; dx <= 1; dx++) {
            int c = ((cy + dy + G) % G) * G + (cx + dx + G) % G;
            for (int j = head[c]; j >= 0; j = nxt[j]) {
                if (j == i) continue;
                double ddx = wrapd(x[j] - x[i]), ddy = wrapd(y[j] - y[i]);
                if (ddx * ddx + ddy * ddy <= r2) k++;
            }
        }
    return k;
}
static void census(long t) {
    long over15 = 0, blue = 0, yellow = 0, brown = 0, mag_printed = 0, mag_first = 0, blue_mf = 0, yellow_mf = 0;
    for (int i = 0; i < n; i++) {
        int n5 = within(i, 5.0), n13 = within(i, 1.3);
        if (n5 > 15) over15++;
        if (n5 > 15 && n5 <= 35) blue++;
        else if (n5 > 35) yellow++;
        else if (n5 >= 13 && n5 <= 15) brown++;
        else if (n13 > 15) mag_printed++;
        if (n13 > 15) mag_first++;
        else if (n5 > 15 && n5 <= 35) blue_mf++;
        else if (n5 > 35) yellow_mf++;
    }
    printf("%ld %ld %ld %ld %ld %ld %ld %ld %ld\n", t, over15, blue, yellow, brown, mag_printed, mag_first, blue_mf, yellow_mf);
}

int main(int argc, char **argv) {
    if (argc < 6) { fprintf(stderr, "usage: pps run|trace seed particles side steps [every mirror]\n"); return 2; }
    int trace = strcmp(argv[1], "trace") == 0;
    uint64_t seed = strtoull(argv[2], 0, 10);
    n = atoi(argv[3]); side = atof(argv[4]);
    long steps = atol(argv[5]);
    long every = trace ? 0 : atol(argv[6]);
    int mirror = trace ? 0 : atoi(argv[7]);
    G = (int)floor(side / RADIUS);
    if (G < 3) { fprintf(stderr, "side too small\n"); return 2; }
    cellw = side / G;
    for (int k = 0; k < 4; k++) s[k] = splitmix(&seed);
    x = malloc(n * sizeof(double)); y = malloc(n * sizeof(double)); phi = malloc(n * sizeof(double));
    head = malloc(G * G * sizeof(int)); nxt = malloc(n * sizeof(int)); prv = malloc(n * sizeof(int));
    cellof = malloc(n * sizeof(int));
    int *order = malloc(n * sizeof(int));
    for (int c = 0; c < G * G; c++) head[c] = -1;
    for (int i = 0; i < n; i++) {
        x[i] = unif() * side; y[i] = unif() * side; phi[i] = unif() * 2 * M_PI;
        insert(i, cell_of(x[i], y[i]));
    }
    const double alpha = M_PI, beta = 17.0 * M_PI / 180.0;
    for (long t = 0;; t++) {
        if (!trace && t % every == 0) { census(t); fflush(stdout); }
        if (t == steps) break;
        for (int i = 0; i < n; i++) order[i] = i;
        for (int i = n - 1; i > 0; i--) {
            int j = (int)below((uint64_t)i + 1);
            int tmp = order[i]; order[i] = order[j]; order[j] = tmp;
        }
        for (int k = 0; k < n; k++) {
            int i = order[k], L, R;
            sense(i, &L, &R);
            int N = L + R, sg = (R > L) - (R < L);
            if (mirror) sg = -sg;
            phi[i] = fmod(phi[i] + alpha + beta * N * sg, 2 * M_PI);
            double nx = x[i] + cos(phi[i]) * SPEED, ny = y[i] + sin(phi[i]) * SPEED;
            nx = fmod(nx + side, side); ny = fmod(ny + side, side);
            if (nx >= side) nx -= side;
            if (ny >= side) ny -= side;
            int c = cell_of(nx, ny);
            x[i] = nx; y[i] = ny;
            if (c != cellof[i]) { removep(i); insert(i, c); }
        }
    }
    if (trace)
        for (int i = 0; i < n; i++) printf("%a %a %a\n", x[i], y[i], phi[i]);
    return 0;
}
