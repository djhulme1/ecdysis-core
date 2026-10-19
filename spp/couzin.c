/* Couzin, Krause, James, Ruxton & Franks (2002), "Collective memory and spatial sorting in animal groups":
 * the zones model, as spp/couzin2002.py's rules state it.
 *
 * Imago's laboratory. Deterministic in plain arithmetic: the only library calls are sqrt, frexp and fabs, which are
 * exact or correctly rounded everywhere; sines, cosines and logarithms are series written here; compile with
 * -ffp-contract=off so that no multiply and add are fused. A run on any IEEE machine gives the same numbers.
 *
 * Usage: couzin <mode> <params file>, mode one of sweep, grid, sort, trace, noise, math.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAXN 400
static const double PI = 3.141592653589793;
static const double LN2 = 0.6931471805599453;

/* ------------------------------------------------------------------ random numbers: xoshiro256** */
typedef struct { uint64_t s[4]; int have; double spare; } rng_t;
static uint64_t splitmix(uint64_t *x) {
    uint64_t z = (*x += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static void rng_seed(rng_t *r, uint64_t seed) {
    uint64_t x = seed;
    for (int i = 0; i < 4; i++) r->s[i] = splitmix(&x);
    r->have = 0;
    r->spare = 0.0;
}
static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t rng_next(rng_t *r) {
    uint64_t *s = r->s;
    uint64_t res = rotl(s[1] * 5, 7) * 9;
    uint64_t t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return res;
}
static double uni(rng_t *r) { return (double)(rng_next(r) >> 11) * (1.0 / 9007199254740992.0); }

/* ------------------------------------------------------------------ deterministic elementary functions */
static double dlog(double x) { /* x > 0 */
    int e;
    double m = frexp(x, &e);            /* m in [0.5, 1) */
    if (m < 0.7071067811865476) { m = m * 2.0; e = e - 1; }
    double z = (m - 1.0) / (m + 1.0);
    double z2 = z * z;
    double s = 1.0 / 29.0;
    for (int k = 27; k >= 1; k -= 2) s = s * z2 + 1.0 / (double)k;
    return 2.0 * z * s + (double)e * LN2;
}
static void dsincos(double x, double *sn, double *cs) {
    if (fabs(x) > 1.0) {
        double s2, c2;
        dsincos(0.5 * x, &s2, &c2);
        *sn = 2.0 * s2 * c2;
        *cs = 1.0 - 2.0 * s2 * s2;
        return;
    }
    double x2 = x * x;
    double ps = 1.0;
    for (int k = 24; k >= 2; k -= 2) ps = 1.0 - x2 / ((double)k * (double)(k + 1)) * ps;
    double pc = 1.0;
    for (int k = 23; k >= 1; k -= 2) pc = 1.0 - x2 / ((double)k * (double)(k + 1)) * pc;
    *sn = x * ps;
    *cs = pc;
}
static double gauss(rng_t *r) { /* Marsaglia's polar method */
    if (r->have) { r->have = 0; return r->spare; }
    double u, v, s;
    do {
        u = 2.0 * uni(r) - 1.0;
        v = 2.0 * uni(r) - 1.0;
        s = u * u + v * v;
    } while (s >= 1.0 || s == 0.0);
    double f = sqrt(-2.0 * dlog(s) / s);
    r->spare = v * f;
    r->have = 1;
    return u * f;
}

/* ------------------------------------------------------------------ vectors */
static inline double dot(const double *a, const double *b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
static inline double norm(const double *a) { return sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]); }
static void unit_in_place(double *a) {
    double n = norm(a);
    a[0] = a[0] / n; a[1] = a[1] / n; a[2] = a[2] / n;
}
static void cross(const double *a, const double *b, double *o) {
    o[0] = a[1] * b[2] - a[2] * b[1];
    o[1] = a[2] * b[0] - a[0] * b[2];
    o[2] = a[0] * b[1] - a[1] * b[0];
}
/* an orthonormal pair perpendicular to the unit vector d */
static void basis(const double *d, double *e1, double *e2) {
    double ax[3] = {0.0, 0.0, 0.0};
    double a0 = fabs(d[0]), a1 = fabs(d[1]), a2 = fabs(d[2]);
    if (a0 <= a1 && a0 <= a2) ax[0] = 1.0; else if (a1 <= a2) ax[1] = 1.0; else ax[2] = 1.0;
    cross(ax, d, e1);
    unit_in_place(e1);
    cross(d, e1, e2);
    unit_in_place(e2);
}

/* ------------------------------------------------------------------ the model */
typedef struct {
    int N;
    double rr_base, ro, ra, alpha, theta, speed, sigma, tau, r0;
    int self_in, normed, noise; /* readings: d_o with the focal individual; d_o, d_a as unit vectors; noise 1 or 2 */
    uint64_t seed;
    /* sweep */
    double ro_lo, ro_step; int n_up, steps_per, window;
    /* grid and sort */
    int steps; int vary; double vary_sd; /* vary: 0 none, 1 speed, 2 r_r */
    int aligned; double spread; /* trace: start aligned along x, spread apart */
} params_t;

typedef struct {
    int N;
    double c[MAXN][3], v[MAXN][3], d[MAXN][3];
    double rr[MAXN], sp[MAXN];
    double ro, ra, cos_half, cosT, sinT, sigma, tau;
    int self_in, normed, noise;
    rng_t rng;
} sim_t;

static void noisy(sim_t *S, double *dd) {
    if (S->sigma == 0.0) return;
    double e1[3], e2[3], w[3], sn, cs;
    basis(dd, e1, e2);
    if (S->noise == 1) {
        double phi = S->sigma * gauss(&S->rng);
        double nw;
        do {
            double g1 = gauss(&S->rng), g2 = gauss(&S->rng);
            for (int k = 0; k < 3; k++) w[k] = g1 * e1[k] + g2 * e2[k];
            nw = norm(w);
        } while (nw == 0.0);
        for (int k = 0; k < 3; k++) w[k] = w[k] / nw;
        dsincos(phi, &sn, &cs);
    } else {
        double g1 = gauss(&S->rng), g2 = gauss(&S->rng);
        for (int k = 0; k < 3; k++) w[k] = S->sigma * g1 * e1[k] + S->sigma * g2 * e2[k];
        double a = norm(w);
        if (a == 0.0) return;
        for (int k = 0; k < 3; k++) w[k] = w[k] / a;
        dsincos(a, &sn, &cs);
    }
    for (int k = 0; k < 3; k++) dd[k] = cs * dd[k] + sn * w[k];
    unit_in_place(dd);
}

static int nr_[MAXN], no_[MAXN], na_[MAXN];
static double dr_[MAXN][3], do_[MAXN][3], da_[MAXN][3];

static void step(sim_t *S) {
    int N = S->N;
    double ra2 = S->ra * S->ra;
    for (int i = 0; i < N; i++) {
        nr_[i] = no_[i] = na_[i] = 0;
        for (int k = 0; k < 3; k++) dr_[i][k] = do_[i][k] = da_[i][k] = 0.0;
    }
    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            double r[3] = {S->c[j][0] - S->c[i][0], S->c[j][1] - S->c[i][1], S->c[j][2] - S->c[i][2]};
            double d2 = r[0] * r[0] + r[1] * r[1] + r[2] * r[2];
            if (d2 > ra2) continue;
            double dist = sqrt(d2);
            double u[3] = {r[0] / dist, r[1] / dist, r[2] / dist};
            double w[3] = {-u[0], -u[1], -u[2]};
            /* i's view of j */
            if (dist < S->rr[i]) {
                nr_[i]++;
                for (int k = 0; k < 3; k++) dr_[i][k] = dr_[i][k] - u[k];
            } else if (dot(S->v[i], u) >= S->cos_half) {
                if (dist < S->ro) {
                    no_[i]++;
                    for (int k = 0; k < 3; k++) do_[i][k] = do_[i][k] + S->v[j][k];
                } else {
                    na_[i]++;
                    for (int k = 0; k < 3; k++) da_[i][k] = da_[i][k] + u[k];
                }
            }
            /* j's view of i */
            if (dist < S->rr[j]) {
                nr_[j]++;
                for (int k = 0; k < 3; k++) dr_[j][k] = dr_[j][k] - w[k];
            } else if (dot(S->v[j], w) >= S->cos_half) {
                if (dist < S->ro) {
                    no_[j]++;
                    for (int k = 0; k < 3; k++) do_[j][k] = do_[j][k] + S->v[i][k];
                } else {
                    na_[j]++;
                    for (int k = 0; k < 3; k++) da_[j][k] = da_[j][k] + w[k];
                }
            }
        }
    }
    for (int i = 0; i < N; i++) {
        double dd[3];
        if (nr_[i] > 0) {
            for (int k = 0; k < 3; k++) dd[k] = dr_[i][k];
        } else {
            double o[3], a[3];
            for (int k = 0; k < 3; k++) { o[k] = do_[i][k]; a[k] = da_[i][k]; }
            if (no_[i] > 0 && S->self_in) for (int k = 0; k < 3; k++) o[k] = o[k] + S->v[i][k];
            if (S->normed) {
                double no = norm(o), na = norm(a);
                if (no_[i] > 0 && no > 0.0) for (int k = 0; k < 3; k++) o[k] = o[k] / no;
                if (na_[i] > 0 && na > 0.0) for (int k = 0; k < 3; k++) a[k] = a[k] / na;
            }
            if (no_[i] > 0 && na_[i] > 0) for (int k = 0; k < 3; k++) dd[k] = 0.5 * (o[k] + a[k]);
            else if (no_[i] > 0) for (int k = 0; k < 3; k++) dd[k] = o[k];
            else if (na_[i] > 0) for (int k = 0; k < 3; k++) dd[k] = a[k];
            else for (int k = 0; k < 3; k++) dd[k] = S->v[i][k];
        }
        if (dd[0] == 0.0 && dd[1] == 0.0 && dd[2] == 0.0) for (int k = 0; k < 3; k++) dd[k] = S->v[i][k];
        unit_in_place(dd);
        noisy(S, dd);
        for (int k = 0; k < 3; k++) S->d[i][k] = dd[k];
    }
    for (int i = 0; i < N; i++) {
        double *v = S->v[i], *dd = S->d[i];
        double c = dot(v, dd);
        if (c > S->cosT) {
            for (int k = 0; k < 3; k++) v[k] = dd[k];
        } else {
            double w[3], nv[3];
            for (int k = 0; k < 3; k++) w[k] = dd[k] - c * v[k];
            double nw = norm(w);
            if (nw == 0.0) {
                double e2[3];
                basis(v, w, e2);
            } else {
                for (int k = 0; k < 3; k++) w[k] = w[k] / nw;
            }
            for (int k = 0; k < 3; k++) nv[k] = S->cosT * v[k] + S->sinT * w[k];
            unit_in_place(nv);
            for (int k = 0; k < 3; k++) v[k] = nv[k];
        }
        double len = S->sp[i] * S->tau;
        for (int k = 0; k < 3; k++) S->c[i][k] = S->c[i][k] + len * v[k];
    }
}

static void measures(const sim_t *S, double *p, double *m) {
    int N = S->N;
    double sv[3] = {0.0, 0.0, 0.0}, cg[3] = {0.0, 0.0, 0.0}, sm[3] = {0.0, 0.0, 0.0};
    for (int i = 0; i < N; i++) for (int k = 0; k < 3; k++) { sv[k] = sv[k] + S->v[i][k]; cg[k] = cg[k] + S->c[i][k]; }
    for (int k = 0; k < 3; k++) cg[k] = cg[k] / (double)N;
    for (int i = 0; i < N; i++) {
        double r[3] = {S->c[i][0] - cg[0], S->c[i][1] - cg[1], S->c[i][2] - cg[2]};
        double nr = norm(r);
        if (nr == 0.0) continue;
        for (int k = 0; k < 3; k++) r[k] = r[k] / nr;
        double x[3];
        cross(r, S->v[i], x);
        for (int k = 0; k < 3; k++) sm[k] = sm[k] + x[k];
    }
    *p = norm(sv) / (double)N;
    *m = norm(sm) / (double)N;
}

static int par[MAXN];
static int find(int a) { while (par[a] != a) { par[a] = par[par[a]]; a = par[a]; } return a; }
static int components(const sim_t *S) {
    int N = S->N, n = N;
    double ra2 = S->ra * S->ra;
    for (int i = 0; i < N; i++) par[i] = i;
    for (int i = 0; i < N; i++) for (int j = i + 1; j < N; j++) {
        double r[3] = {S->c[j][0] - S->c[i][0], S->c[j][1] - S->c[i][1], S->c[j][2] - S->c[i][2]};
        double d2 = dot(r, r);
        if (d2 > ra2) continue;
        double dist = sqrt(d2);
        double u[3] = {r[0] / dist, r[1] / dist, r[2] / dist}, w[3] = {-u[0], -u[1], -u[2]};
        int seen = dist < S->rr[i] || dist < S->rr[j] || dot(S->v[i], u) >= S->cos_half || dot(S->v[j], w) >= S->cos_half;
        if (!seen) continue;
        int a = find(i), b = find(j);
        if (a != b) { par[a] = b; n--; }
    }
    return n;
}

static int detects_one(const sim_t *S, int i) {
    double ra2 = S->ra * S->ra;
    for (int j = 0; j < S->N; j++) {
        if (j == i) continue;
        double r[3] = {S->c[j][0] - S->c[i][0], S->c[j][1] - S->c[i][1], S->c[j][2] - S->c[i][2]};
        double d2 = dot(r, r);
        if (d2 > ra2) continue;
        double dist = sqrt(d2);
        double u[3] = {r[0] / dist, r[1] / dist, r[2] / dist};
        if (dist < S->rr[i] || dot(S->v[i], u) >= S->cos_half) return 1;
    }
    return 0;
}

static void init(sim_t *S, const params_t *P) {
    S->N = P->N;
    S->ro = P->ro; S->ra = P->ra; S->sigma = P->sigma; S->tau = P->tau;
    S->self_in = P->self_in; S->normed = P->normed; S->noise = P->noise;
    S->cos_half = -sqrt(0.5); /* placeholder, set below */
    double sn, cs;
    dsincos(P->alpha / 2.0 * PI / 180.0, &sn, &cs);
    S->cos_half = cs;
    if (P->alpha >= 360.0) S->cos_half = -2.0; /* no blind volume */
    dsincos(P->theta * P->tau * PI / 180.0, &sn, &cs);
    S->cosT = cs; S->sinT = sn;
    rng_seed(&S->rng, P->seed);
    for (int i = 0; i < S->N; i++) { S->rr[i] = P->rr_base; S->sp[i] = P->speed; }
    for (;;) {
        for (int i = 0; i < S->N; i++) {
            if (P->aligned) {
                S->c[i][0] = 0.0; S->c[i][1] = P->spread * (double)i; S->c[i][2] = 0.0;
                S->v[i][0] = 1.0; S->v[i][1] = 0.0; S->v[i][2] = 0.0;
                continue;
            }
            double x, y, z;
            do {
                x = 2.0 * uni(&S->rng) - 1.0; y = 2.0 * uni(&S->rng) - 1.0; z = 2.0 * uni(&S->rng) - 1.0;
            } while (x * x + y * y + z * z > 1.0);
            S->c[i][0] = P->r0 * x; S->c[i][1] = P->r0 * y; S->c[i][2] = P->r0 * z;
            double g[3], ng;
            do {
                g[0] = gauss(&S->rng); g[1] = gauss(&S->rng); g[2] = gauss(&S->rng);
                ng = norm(g);
            } while (ng == 0.0);
            for (int k = 0; k < 3; k++) S->v[i][k] = g[k] / ng;
        }
        if (P->aligned) break;
        int ok = 1;
        for (int i = 0; i < S->N && ok; i++) ok = detects_one(S, i);
        if (ok) break;
    }
    if (P->vary) {
        for (int i = 0; i < S->N; i++) {
            double x;
            do {
                x = (P->vary == 1 ? P->speed : P->rr_base) + P->vary_sd * gauss(&S->rng);
            } while (x <= 0.0 || (P->vary == 2 && x >= P->ro));
            if (P->vary == 1) S->sp[i] = x; else S->rr[i] = x;
        }
    }
}

/* ------------------------------------------------------------------ parameters */
static void read_params(const char *path, params_t *P) {
    memset(P, 0, sizeof(*P));
    P->N = 100; P->rr_base = 1.0; P->ro = 2.0; P->ra = 14.0; P->alpha = 270.0; P->theta = 40.0; P->speed = 3.0;
    P->sigma = 0.05; P->tau = 0.1; P->r0 = 5.0; P->noise = 1;
    FILE *f = fopen(path, "r");
    if (!f) { fprintf(stderr, "no params\n"); exit(2); }
    char key[64]; char val[128];
    while (fscanf(f, "%63s %127s", key, val) == 2) {
        if (!strcmp(key, "N")) P->N = atoi(val);
        else if (!strcmp(key, "rr")) P->rr_base = strtod(val, 0);
        else if (!strcmp(key, "ro")) P->ro = strtod(val, 0);
        else if (!strcmp(key, "ra")) P->ra = strtod(val, 0);
        else if (!strcmp(key, "alpha")) P->alpha = strtod(val, 0);
        else if (!strcmp(key, "theta")) P->theta = strtod(val, 0);
        else if (!strcmp(key, "speed")) P->speed = strtod(val, 0);
        else if (!strcmp(key, "sigma")) P->sigma = strtod(val, 0);
        else if (!strcmp(key, "tau")) P->tau = strtod(val, 0);
        else if (!strcmp(key, "r0")) P->r0 = strtod(val, 0);
        else if (!strcmp(key, "self")) P->self_in = atoi(val);
        else if (!strcmp(key, "normed")) P->normed = atoi(val);
        else if (!strcmp(key, "noise")) P->noise = atoi(val);
        else if (!strcmp(key, "seed")) P->seed = strtoull(val, 0, 10);
        else if (!strcmp(key, "ro_lo")) P->ro_lo = strtod(val, 0);
        else if (!strcmp(key, "ro_step")) P->ro_step = strtod(val, 0);
        else if (!strcmp(key, "n_up")) P->n_up = atoi(val);
        else if (!strcmp(key, "steps_per")) P->steps_per = atoi(val);
        else if (!strcmp(key, "window")) P->window = atoi(val);
        else if (!strcmp(key, "steps")) P->steps = atoi(val);
        else if (!strcmp(key, "vary")) P->vary = atoi(val);
        else if (!strcmp(key, "vary_sd")) P->vary_sd = strtod(val, 0);
        else if (!strcmp(key, "aligned")) P->aligned = atoi(val);
        else if (!strcmp(key, "spread")) P->spread = strtod(val, 0);
        else { fprintf(stderr, "unknown key %s\n", key); exit(2); }
    }
    fclose(f);
    if (P->N < 2 || P->N > MAXN) { fprintf(stderr, "bad N\n"); exit(2); }
}

/* run `steps` steps at the current r_o; report the state at the end and the means over the last `window` steps */
static void hold(sim_t *S, int steps, int window, const char *tag, int idx) {
    double sp = 0.0, sm = 0.0, p, m;
    for (int t = 1; t <= steps; t++) {
        step(S);
        if (t > steps - window) { measures(S, &p, &m); sp = sp + p; sm = sm + m; }
    }
    measures(S, &p, &m);
    int nc = components(S);
    printf("%s %d %.17g %.17g %.17g %.17g %.17g %d\n", tag, idx, S->ro, p, m, sp / (double)window, sm / (double)window, nc);
}

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: couzin mode params\n"); return 2; }
    params_t P;
    read_params(argv[2], &P);
    static sim_t S;
    const char *mode = argv[1];
    if (!strcmp(mode, "math")) {
        /* the series against nothing: print them for the driver to compare with its own libm */
        rng_seed(&S.rng, P.seed);
        for (int k = 0; k < 2000; k++) {
            double x = (double)(k - 1000) / 250.0, sn, cs;
            dsincos(x, &sn, &cs);
            double y = (double)(k + 1) / 500.0;
            printf("m %.17g %.17g %.17g %.17g %.17g\n", x, sn, cs, y, dlog(y));
        }
        return 0;
    }
    if (!strcmp(mode, "noise")) {
        /* one free individual (no others), sigma as given: the angle turned at each step */
        P.N = 2; P.aligned = 1; P.spread = 1.0e6;
        init(&S, &P);
        double sum = 0.0, sum2 = 0.0;
        for (int t = 0; t < P.steps; t++) {
            double v0[3] = {S.v[0][0], S.v[0][1], S.v[0][2]};
            step(&S);
            double c = dot(v0, S.v[0]);
            if (c > 1.0) c = 1.0;
            double w[3];
            cross(v0, S.v[0], w);
            double s = norm(w);
            /* the sine and 1 - cosine of the angle turned, averaged (no inverse trigonometry needed) */
            sum = sum + s; sum2 = sum2 + (1.0 - c);
        }
        printf("noise %.17g %.17g %d\n", sum / (double)P.steps, sum2 / (double)P.steps, P.steps);
        return 0;
    }
    S.N = P.N;
    if (!strcmp(mode, "sweep")) {
        P.ro = P.ro_lo;
        init(&S, &P);
        for (int k = 0; k < P.n_up; k++) {
            S.ro = P.ro_lo + P.ro_step * (double)k;
            hold(&S, P.steps_per, P.window, "up", k);
        }
        for (int k = P.n_up - 2; k >= 0; k--) {
            S.ro = P.ro_lo + P.ro_step * (double)k;
            hold(&S, P.steps_per, P.window, "down", k);
        }
        return 0;
    }
    if (!strcmp(mode, "grid")) {
        init(&S, &P);
        hold(&S, P.steps, P.window, "grid", 0);
        return 0;
    }
    if (!strcmp(mode, "sort")) {
        init(&S, &P);
        for (int t = 0; t < P.steps; t++) step(&S);
        double p, m;
        measures(&S, &p, &m);
        printf("state %.17g %.17g %d\n", p, m, components(&S));
        for (int i = 0; i < S.N; i++)
            printf("ind %d %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g\n", i, S.sp[i], S.rr[i], S.c[i][0], S.c[i][1],
                   S.c[i][2], S.v[i][0], S.v[i][1], S.v[i][2]);
        return 0;
    }
    if (!strcmp(mode, "trace")) {
        init(&S, &P);
        for (int i = 0; i < S.N; i++)
            printf("t0 %d %.17g %.17g %.17g %.17g %.17g %.17g\n", i, S.c[i][0], S.c[i][1], S.c[i][2], S.v[i][0], S.v[i][1], S.v[i][2]);
        for (int t = 0; t < P.steps; t++) step(&S);
        for (int i = 0; i < S.N; i++)
            printf("t1 %d %.17g %.17g %.17g %.17g %.17g %.17g\n", i, S.c[i][0], S.c[i][1], S.c[i][2], S.v[i][0], S.v[i][1], S.v[i][2]);
        double p, m;
        measures(&S, &p, &m);
        printf("pm %.17g %.17g %d\n", p, m, components(&S));
        return 0;
    }
    fprintf(stderr, "unknown mode\n");
    return 2;
}
