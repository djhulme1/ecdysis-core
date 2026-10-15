/* spp/vicsek.c: the self-driven particles of Vicsek, Czirok, Ben-Jacob, Cohen & Shochet (1995), as the paper states them.
 *
 * Imago's laboratory; the engine of spp/vicsek.py (ext:8fcb3415efefaef9), whose docstring states the rules. N points
 * in a square of side L with periodic boundaries, each moving a distance v per step; at each step every particle's new
 * direction is the direction of the summed velocities of the particles (itself included) within distance r of it,
 * arctg(<sin theta>/<cos theta>) taken in its quadrant (atan2), plus a noise uniform on [-eta/2, eta/2); then every
 * position moves by its old velocity, x(t+1) = x(t) + v(t) (the paper's equations 1 and 2). Neighbours are found in
 * cells of side at least r, at least four to a side (or by brute force, mode 1, or when L < 4r), sorted by index and
 * summed in that order, and every offset is corrected to the nearest image by the same arithmetic in both searches,
 * so that they give the same numbers to the last bit. v_a(t) is measured on the directions at the start of step t.
 *
 *   vicsek run PARAMS     prints "va mean mean2 mean4 n" over the measured steps, "block k mean" for each block of
 *                         `block` measured steps, and "end x0 y0 th0" (particle 0's final state) for checks;
 *   vicsek trace PARAMS   prints, after the last step, "p i x y theta" for every particle (%.17g), for the tests.
 *
 * PARAMS: "key value" lines: N, L, v, r, eta, steps (measured), burn (discarded first), block, seed, mode (0 cells, 1
 * brute force), align (1: every particle starts with direction 0, else uniform on [-pi, pi)).
 * Random numbers: xoshiro256** seeded through splitmix64 from seed; the start draws x, y, theta for each particle in
 * turn (x = L u, y = L u, theta = pi (2u - 1)), and each step draws one noise per particle in index order,
 * (u - 1/2) eta. u = (next() >> 11) 2^-53.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const double PI = 3.14159265358979323846; /* math.pi, the same double */
typedef struct { int N, mode, align; double L, v, r, eta; long long steps, burn, block; uint64_t seed; } Par;
static Par P;
static uint64_t s[4];
static uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t next(void) {
    uint64_t res = rotl(s[1] * 5, 7) * 9, t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return res;
}
static void seed_rng(uint64_t x) {
    for (int i = 0; i < 4; i++) {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        s[i] = z ^ (z >> 31);
    }
}
static double uni(void) { return (next() >> 11) * 0x1.0p-53; }
static void die(const char *m) { fprintf(stderr, "vicsek: %s\n", m); exit(2); }

static void read_par(const char *path) {
    FILE *f = fopen(path, "r");
    char k[64], val[128];
    if (!f) die("cannot open params");
    memset(&P, 0, sizeof P);
    P.r = 1.0; P.block = 1000;
    while (fscanf(f, "%63s %127s", k, val) == 2) {
        if (!strcmp(k, "N")) P.N = atoi(val);
        else if (!strcmp(k, "L")) P.L = atof(val);
        else if (!strcmp(k, "v")) P.v = atof(val);
        else if (!strcmp(k, "r")) P.r = atof(val);
        else if (!strcmp(k, "eta")) P.eta = atof(val);
        else if (!strcmp(k, "steps")) P.steps = atoll(val);
        else if (!strcmp(k, "burn")) P.burn = atoll(val);
        else if (!strcmp(k, "block")) P.block = atoll(val);
        else if (!strcmp(k, "seed")) P.seed = strtoull(val, NULL, 10);
        else if (!strcmp(k, "mode")) P.mode = atoi(val);
        else if (!strcmp(k, "align")) P.align = atoi(val);
        else die("unknown key");
    }
    fclose(f);
    if (P.N < 1 || P.N > 200000 || !(P.L > 2 * P.r) || P.r <= 0 || P.v < 0 || P.v >= P.L || P.eta < 0 || P.steps < 0 ||
        P.burn < 0 || P.block < 1)
        die("bad params");
}

static double *x, *y, *th, *sn, *cs, *nth, *px, *py, *nsx, *nsy;
static int *cid, *cstart, *order, *buf, *nbc;
static int ncell;
static double csize;

static int cell_of(double a) {
    int c = (int)(a / csize);
    return c >= ncell ? ncell - 1 : (c < 0 ? 0 : c);
}
static int neighbours(int i) { /* fills buf with the indices within r of i, ascending; returns the count */
    int n = 0;
    const double half = P.L / 2, r2 = P.r * P.r;
    if (P.mode == 1 || ncell < 4) {
        for (int j = 0; j < P.N; j++) {
            double dx = x[j] - x[i], dy = y[j] - y[i];
            if (dx > half) dx -= P.L; else if (dx < -half) dx += P.L;
            if (dy > half) dy -= P.L; else if (dy < -half) dy += P.L;
            if (dx * dx + dy * dy <= r2) buf[n++] = j;
        }
        return n;
    }
    const int c0 = cid[i];
    const double xi = x[i], yi = y[i];
    for (int m = 0; m < 9; m++) {
        const int c = nbc[9 * c0 + m];
        const double sx = nsx[9 * c0 + m], sy = nsy[9 * c0 + m];
        for (int k = cstart[c]; k < cstart[c + 1]; k++) {
            double dx = px[k] - xi, dy = py[k] - yi;
            if (sx != 0) dx += sx; /* the brute force's dx -= L or dx += L: the same operation on the same operand */
            if (sy != 0) dy += sy;
            if (dx * dx + dy * dy <= r2) buf[n++] = order[k];
        }
    }
    for (int a = 1; a < n; a++) { /* insertion sort: index order, as the brute force gives */
        int t = buf[a], b = a - 1;
        while (b >= 0 && buf[b] > t) { buf[b + 1] = buf[b]; b--; }
        buf[b + 1] = t;
    }
    return n;
}

int main(int argc, char **argv) {
    if (argc < 3) die("usage: vicsek run|trace PARAMS");
    int trace = !strcmp(argv[1], "trace");
    if (!trace && strcmp(argv[1], "run")) die("unknown mode");
    read_par(argv[2]);
    const int N = P.N;
    x = malloc(sizeof(double) * N); y = malloc(sizeof(double) * N); th = malloc(sizeof(double) * N);
    sn = malloc(sizeof(double) * N); cs = malloc(sizeof(double) * N); nth = malloc(sizeof(double) * N);
    buf = malloc(sizeof(int) * N); cid = malloc(sizeof(int) * N); order = malloc(sizeof(int) * N);
    px = malloc(sizeof(double) * N); py = malloc(sizeof(double) * N);
    ncell = (int)floor(P.L / P.r);
    if (ncell > 2000) ncell = 2000;
    csize = P.L / ncell;
    const int nc2 = ncell * ncell;
    cstart = malloc(sizeof(int) * (size_t)(nc2 + 1));
    nbc = malloc(sizeof(int) * 9 * (size_t)nc2);
    nsx = malloc(sizeof(double) * 9 * (size_t)nc2); nsy = malloc(sizeof(double) * 9 * (size_t)nc2);
    for (int cx = 0; cx < ncell; cx++)
        for (int cy = 0; cy < ncell; cy++) {
            int m = 0;
            for (int ox = -1; ox <= 1; ox++)
                for (int oy = -1; oy <= 1; oy++, m++) {
                    int ax = cx + ox, ay = cy + oy;
                    double sx = 0, sy = 0;
                    if (ax < 0) { ax += ncell; sx = -P.L; } else if (ax >= ncell) { ax -= ncell; sx = P.L; }
                    if (ay < 0) { ay += ncell; sy = -P.L; } else if (ay >= ncell) { ay -= ncell; sy = P.L; }
                    /* a cell across the left edge holds x_j near L: x_j - x_i > L/2, which the nearest image lowers by L */
                    nbc[9 * (cx * ncell + cy) + m] = ax * ncell + ay;
                    nsx[9 * (cx * ncell + cy) + m] = sx;
                    nsy[9 * (cx * ncell + cy) + m] = sy;
                }
        }
    seed_rng(P.seed);
    for (int i = 0; i < N; i++) {
        x[i] = P.L * uni();
        y[i] = P.L * uni();
        double a = PI * (2 * uni() - 1);
        th[i] = P.align ? 0.0 : a;
    }
    double m1 = 0, m2 = 0, m4 = 0, bsum = 0;
    long long nmeas = 0, nb = 0;
    const long long total = P.burn + P.steps;
    for (long long t = 0; t < total; t++) {
        for (int i = 0; i < N; i++) { sn[i] = sin(th[i]); cs[i] = cos(th[i]); }
        if (t >= P.burn) {
            double sx = 0, sy = 0;
            for (int i = 0; i < N; i++) { sx += cs[i]; sy += sn[i]; }
            double va = sqrt(sx * sx + sy * sy) / N;
            m1 += va; m2 += va * va; m4 += va * va * va * va; nmeas++;
            bsum += va;
            if (nmeas % P.block == 0) { printf("block %lld %.12g\n", nb++, bsum / P.block); bsum = 0; }
        }
        if (!(P.mode == 1 || ncell < 4)) { /* counting sort by cell, index order kept within each cell */
            for (int c = 0; c <= nc2; c++) cstart[c] = 0;
            for (int i = 0; i < N; i++) { cid[i] = cell_of(x[i]) * ncell + cell_of(y[i]); cstart[cid[i] + 1]++; }
            for (int c = 0; c < nc2; c++) cstart[c + 1] += cstart[c];
            for (int i = 0; i < N; i++) { int k = cstart[cid[i]]++; order[k] = i; px[k] = x[i]; py[k] = y[i]; }
            for (int c = nc2; c > 0; c--) cstart[c] = cstart[c - 1];
            cstart[0] = 0;
        }
        for (int i = 0; i < N; i++) {
            int n = neighbours(i);
            double ss = 0, cc = 0;
            for (int a = 0; a < n; a++) { ss += sn[buf[a]]; cc += cs[buf[a]]; }
            nth[i] = atan2(ss, cc) + (uni() - 0.5) * P.eta;
        }
        for (int i = 0; i < N; i++) {
            x[i] += P.v * cs[i];
            y[i] += P.v * sn[i];
            if (x[i] >= P.L) x[i] -= P.L; else if (x[i] < 0) x[i] += P.L;
            if (y[i] >= P.L) y[i] -= P.L; else if (y[i] < 0) y[i] += P.L;
            th[i] = nth[i];
        }
    }
    if (nmeas) printf("va %.12g %.12g %.12g %lld\n", m1 / nmeas, m2 / nmeas, m4 / nmeas, nmeas);
    else printf("va nan nan nan 0\n");
    printf("end %.17g %.17g %.17g\n", x[0], y[0], th[0]);
    if (trace)
        for (int i = 0; i < N; i++) printf("p %d %.17g %.17g %.17g\n", i, x[i], y[i], th[i]);
    return 0;
}
